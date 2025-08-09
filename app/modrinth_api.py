"""
Клиент для работы с Modrinth API
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
import httpx
from app.models import ModLoader, VersionType
import logging

logger = logging.getLogger(__name__)


class ModrinthAPIError(Exception):
    """Ошибка при работе с Modrinth API"""
    pass


class ModrinthClient:
    """Асинхронный клиент для Modrinth API"""
    
    BASE_URL = "https://api.modrinth.com/v2"
    
    def __init__(self, cache_ttl: int = 300):
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "MinecraftModManager/1.0.0 (https://github.com/user/minecraft-mod-manager)"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self._client:
            await self._client.aclose()
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Создать ключ кэша"""
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"{endpoint}?{param_str}"
        return endpoint
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Проверить актуальность кэша"""
        return datetime.now() - timestamp < timedelta(seconds=self.cache_ttl)
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Выполнить HTTP запрос с кэшированием"""
        if not self._client:
            raise ModrinthAPIError("HTTP клиент не инициализирован")
        
        cache_key = self._get_cache_key(endpoint, params)
        
        # Проверяем кэш
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.debug(f"Используем кэш для {cache_key}")
                return data
        
        # Выполняем запрос
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            logger.debug(f"Запрос к API: {url}")
            response = await self._client.get(url, params=params or {})
            response.raise_for_status()
            
            data = response.json()
            
            # Сохраняем в кэш
            self._cache[cache_key] = (datetime.now(), data)
            
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ModrinthAPIError(f"Проект не найден: {endpoint}")
            elif e.response.status_code == 429:
                raise ModrinthAPIError("Превышен лимит запросов к API")
            else:
                raise ModrinthAPIError(f"Ошибка API ({e.response.status_code}): {e.response.text}")
        except httpx.RequestError as e:
            raise ModrinthAPIError(f"Ошибка сети: {e}")
    
    def extract_slug_from_url(self, url_or_slug: str) -> str:
        """Извлечь slug из URL или вернуть как есть"""
        # Если это уже slug (без протокола и доменов)
        if not url_or_slug.startswith(('http://', 'https://')):
            return url_or_slug.strip()
        
        # Парсим URL
        try:
            parsed = urlparse(url_or_slug)
            if 'modrinth.com' not in parsed.netloc:
                raise ModrinthAPIError(f"Неподдерживаемый URL: {url_or_slug}")
            
            # Извлекаем slug из пути
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'mod':
                return path_parts[1]
            
            raise ModrinthAPIError(f"Не удалось извлечь slug из URL: {url_or_slug}")
            
        except Exception as e:
            raise ModrinthAPIError(f"Ошибка парсинга URL: {e}")
    
    async def get_project(self, slug: str) -> Dict:
        """Получить информацию о проекте"""
        slug = self.extract_slug_from_url(slug)
        return await self._make_request(f"project/{slug}")
    
    async def get_project_versions(self, slug: str, 
                                 game_versions: List[str] = None,
                                 loaders: List[str] = None) -> List[Dict]:
        """Получить версии проекта"""
        slug = self.extract_slug_from_url(slug)
        
        params = {}
        if game_versions:
            params['game_versions'] = json.dumps(game_versions)
        if loaders:
            params['loaders'] = json.dumps(loaders)
        
        return await self._make_request(f"project/{slug}/version", params)
    
    async def get_version(self, version_id: str) -> Dict:
        """Получить информацию о конкретной версии"""
        return await self._make_request(f"version/{version_id}")
    
    async def search_projects(self, query: str, 
                            categories: List[str] = None,
                            versions: List[str] = None,
                            limit: int = 10) -> Dict:
        """Поиск проектов"""
        params = {
            'query': query,
            'limit': limit
        }
        
        if categories:
            params['categories'] = json.dumps(categories)
        if versions:
            params['versions'] = json.dumps(versions)
        
        return await self._make_request("search", params)
    
    def filter_compatible_versions(self, versions: List[Dict], 
                                 minecraft_version: str,
                                 mod_loader: ModLoader,
                                 prefer_stable: bool = True) -> List[Dict]:
        """Отфильтровать совместимые версии"""
        compatible = []
        
        for version in versions:
            # Проверяем совместимость с версией Minecraft
            if minecraft_version not in version.get('game_versions', []):
                continue
            
            # Проверяем совместимость с загрузчиком
            loaders = version.get('loaders', [])
            if mod_loader.value not in loaders:
                continue
            
            compatible.append(version)
        
        if not compatible:
            return []
        
        # Сортируем по приоритету: release > beta > alpha
        def version_priority(v):
            version_type = v.get('version_type', 'release')
            priority_map = {'release': 0, 'beta': 1, 'alpha': 2}
            return priority_map.get(version_type, 3)
        
        if prefer_stable:
            # Сначала пробуем найти стабильные версии
            stable_versions = [v for v in compatible if v.get('version_type') == 'release']
            if stable_versions:
                return sorted(stable_versions, key=lambda x: x.get('date_published', ''), reverse=True)
        
        # Если стабильных нет или не требуем стабильные, возвращаем все отсортированные
        return sorted(compatible, key=lambda x: (version_priority(x), x.get('date_published', '')), reverse=True)
    
    def get_primary_file(self, version: Dict) -> Optional[Dict]:
        """Получить основной файл версии"""
        files = version.get('files', [])
        if not files:
            return None
        
        # Ищем primary файл
        for file in files:
            if file.get('primary', False):
                return file
        
        # Если primary не найден, берем первый .jar файл
        for file in files:
            if file.get('filename', '').endswith('.jar'):
                return file
        
        # В крайнем случае берем первый файл
        return files[0]
    
    async def resolve_dependencies(self, project_slug: str, 
                                 minecraft_version: str,
                                 mod_loader: ModLoader,
                                 resolved: set = None) -> List[Dict]:
        """Рекурсивно разрешить зависимости мода"""
        if resolved is None:
            resolved = set()
        
        if project_slug in resolved:
            return []  # Избегаем циклических зависимостей
        
        resolved.add(project_slug)
        dependencies = []
        
        try:
            # Получаем информацию о проекте
            project = await self.get_project(project_slug)
            versions = await self.get_project_versions(
                project_slug, 
                game_versions=[minecraft_version],
                loaders=[mod_loader.value]
            )
            
            compatible_versions = self.filter_compatible_versions(
                versions, minecraft_version, mod_loader
            )
            
            if not compatible_versions:
                logger.warning(f"Нет совместимых версий для зависимости {project_slug}")
                return dependencies
            
            latest_version = compatible_versions[0]
            
            # Добавляем текущий проект в зависимости
            dependencies.append({
                'project': project,
                'version': latest_version,
                'file': self.get_primary_file(latest_version)
            })
            
            # Обрабатываем зависимости этого проекта
            for dep in latest_version.get('dependencies', []):
                dep_type = dep.get('dependency_type')
                if dep_type in ['required', 'optional']:  # Обрабатываем обязательные и опциональные
                    dep_project_id = dep.get('project_id')
                    if dep_project_id:
                        try:
                            # Получаем slug по project_id
                            dep_project = await self.get_project(dep_project_id)
                            dep_slug = dep_project.get('slug')
                            
                            if dep_slug and dep_slug not in resolved:
                                sub_deps = await self.resolve_dependencies(
                                    dep_slug, minecraft_version, mod_loader, resolved
                                )
                                dependencies.extend(sub_deps)
                        except ModrinthAPIError as e:
                            logger.warning(f"Не удалось разрешить зависимость {dep_project_id}: {e}")
            
        except ModrinthAPIError as e:
            logger.error(f"Ошибка при разрешении зависимостей для {project_slug}: {e}")
        
        return dependencies
    
    async def download_file(self, file_info: Dict, destination_path: str) -> bool:
        """Скачать файл"""
        if not self._client:
            raise ModrinthAPIError("HTTP клиент не инициализирован")
        
        url = file_info.get('url')
        if not url:
            raise ModrinthAPIError("URL файла не найден")
        
        try:
            logger.info(f"Скачивание файла: {file_info.get('filename')}")
            
            async with self._client.stream('GET', url) as response:
                response.raise_for_status()
                
                with open(destination_path, 'wb') as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            
            logger.info(f"Файл успешно скачан: {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            return False
    
    def clear_cache(self):
        """Очистить кэш"""
        self._cache.clear()
        logger.debug("Кэш API очищен")


# Импорт json для использования в методах
import json