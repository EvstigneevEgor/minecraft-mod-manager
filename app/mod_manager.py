"""
Основной модуль управления модами Minecraft
"""

import asyncio
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging

from app.config import Settings
from app.models import ModInfo, ModLoader, InstallResponse, ErrorResponse
from app.modrinth_api import ModrinthClient, ModrinthAPIError

logger = logging.getLogger(__name__)


class ModManagerError(Exception):
    """Ошибка менеджера модов"""
    pass


class ServerInfoReader:
    """Класс для чтения информации о сервере Minecraft"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def read_minecraft_version(self) -> Optional[str]:
        """Определить версию Minecraft сервера"""
        # Сначала пробуем прочитать из server.properties
        version = self._read_version_from_properties()
        if version:
            return version
        
        # Если не найдено, пробуем из логов
        version = self._read_version_from_logs()
        if version:
            return version
        
        logger.warning("Не удалось определить версию Minecraft сервера")
        return None
    
    def _read_version_from_properties(self) -> Optional[str]:
        """Прочитать версию из server.properties"""
        properties_file = self.settings.server_properties_file_path
        
        if not properties_file.exists():
            logger.debug(f"Файл server.properties не найден: {properties_file}")
            return None
        
        try:
            with open(properties_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('version=') or line.startswith('minecraft-version='):
                        version = line.split('=', 1)[1].strip()
                        if version:
                            logger.info(f"Версия из server.properties: {version}")
                            return version
        except Exception as e:
            logger.error(f"Ошибка чтения server.properties: {e}")
        
        return None
    
    def _read_version_from_logs(self) -> Optional[str]:
        """Прочитать версию из логов сервера"""
        log_file = self.settings.latest_log_path
        
        if not log_file.exists():
            logger.debug(f"Файл логов не найден: {log_file}")
            return None
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Читаем последние 100 строк для поиска версии
                lines = f.readlines()[-100:]
                
                for line in reversed(lines):
                    # Ищем паттерны версии в логах
                    patterns = [
                        r'Starting minecraft server version (\d+\.\d+(?:\.\d+)?)',
                        r'Loading Minecraft (\d+\.\d+(?:\.\d+)?)',
                        r'minecraft.*?(\d+\.\d+(?:\.\d+)?)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            version = match.group(1)
                            logger.info(f"Версия из логов: {version}")
                            return version
        except Exception as e:
            logger.error(f"Ошибка чтения логов: {e}")
        
        return None
    
    def detect_mod_loader(self) -> ModLoader:
        """Определить тип загрузчика модов"""
        minecraft_path = Path(self.settings.minecraft_root_path)
        
        # Проверяем наличие файлов Fabric
        fabric_files = [
            'fabric-server-mc.*.jar',
            'fabric-loader-*.jar',
            '.fabric'
        ]
        
        for pattern in fabric_files:
            if list(minecraft_path.glob(pattern)):
                logger.info("Обнаружен Fabric загрузчик")
                return ModLoader.FABRIC
        
        # Проверяем наличие файлов Forge
        forge_files = [
            'forge-*.jar',
            'minecraft_server.*.jar',
            'libraries/net/minecraftforge'
        ]
        
        for pattern in forge_files:
            if list(minecraft_path.glob(pattern)):
                logger.info("Обнаружен Forge загрузчик")
                return ModLoader.FORGE
        
        # По умолчанию возвращаем из настроек
        logger.info(f"Загрузчик не определен, используем из настроек: {self.settings.mod_loader}")
        return ModLoader(self.settings.mod_loader)


class StateManager:
    """Менеджер состояния установленных модов"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.state_file = settings.state_file_path
        self._state: Dict[str, Dict] = {}
        self._load_state()
    
    def _load_state(self):
        """Загрузить состояние из файла"""
        if not self.state_file.exists():
            logger.info("Файл состояния не найден, создаем новый")
            self._state = {
                'mods': {},
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }
            self._save_state()
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self._state = json.load(f)
            
            # Проверяем структуру
            if 'mods' not in self._state:
                self._state['mods'] = {}
            if 'metadata' not in self._state:
                self._state['metadata'] = {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            
            logger.info(f"Загружено состояние: {len(self._state['mods'])} модов")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
            # Создаем резервную копию поврежденного файла
            if self.state_file.exists():
                backup_path = self.state_file.with_suffix('.json.backup')
                shutil.copy2(self.state_file, backup_path)
                logger.info(f"Создана резервная копия: {backup_path}")
            
            # Инициализируем пустое состояние
            self._state = {
                'mods': {},
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0.0'
                }
            }
    
    def _save_state(self):
        """Сохранить состояние в файл"""
        try:
            # Создаем резервную копию если включено
            if self.settings.backup_state and self.state_file.exists():
                backup_path = self.state_file.with_suffix('.json.backup')
                shutil.copy2(self.state_file, backup_path)
            
            # Обновляем метаданные
            self._state['metadata']['updated_at'] = datetime.now().isoformat()
            
            # Сохраняем состояние
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug("Состояние сохранено")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")
            raise ModManagerError(f"Не удалось сохранить состояние: {e}")
    
    def add_mod(self, mod_info: ModInfo):
        """Добавить мод в состояние"""
        self._state['mods'][mod_info.slug] = mod_info.model_dump()
        self._save_state()
        logger.info(f"Мод добавлен в состояние: {mod_info.slug}")
    
    def remove_mod(self, slug: str):
        """Удалить мод из состояния"""
        if slug in self._state['mods']:
            del self._state['mods'][slug]
            self._save_state()
            logger.info(f"Мод удален из состояния: {slug}")
    
    def get_mod(self, slug: str) -> Optional[ModInfo]:
        """Получить информацию о моде"""
        mod_data = self._state['mods'].get(slug)
        if mod_data:
            return ModInfo(**mod_data)
        return None
    
    def get_all_mods(self) -> List[ModInfo]:
        """Получить все установленные моды"""
        mods = []
        for mod_data in self._state['mods'].values():
            try:
                mods.append(ModInfo(**mod_data))
            except Exception as e:
                logger.error(f"Ошибка парсинга мода: {e}")
        return mods
    
    def update_mod(self, slug: str, **kwargs):
        """Обновить информацию о моде"""
        if slug in self._state['mods']:
            self._state['mods'][slug].update(kwargs)
            self._save_state()


class ModManager:
    """Основной менеджер модов"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.server_info = ServerInfoReader(settings)
        self.state_manager = StateManager(settings)
        self._minecraft_version: Optional[str] = None
        self._mod_loader: Optional[ModLoader] = None
    
    async def initialize(self):
        """Инициализация менеджера"""
        # Определяем версию Minecraft
        self._minecraft_version = self.server_info.read_minecraft_version()
        if not self._minecraft_version:
            raise ModManagerError("Не удалось определить версию Minecraft сервера")
        
        # Определяем загрузчик модов
        self._mod_loader = self.server_info.detect_mod_loader()
        
        # Создаем папку модов если её нет
        self.settings.mods_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Менеджер инициализирован: Minecraft {self._minecraft_version}, {self._mod_loader.value}")
    
    @property
    def minecraft_version(self) -> str:
        """Версия Minecraft"""
        if not self._minecraft_version:
            raise ModManagerError("Менеджер не инициализирован")
        return self._minecraft_version
    
    @property
    def mod_loader(self) -> ModLoader:
        """Загрузчик модов"""
        if not self._mod_loader:
            raise ModManagerError("Менеджер не инициализирован")
        return self._mod_loader
    
    def _get_mod_file_path(self, filename: str) -> Path:
        """Получить путь к файлу мода"""
        return self.settings.mods_path / filename
    
    def _is_mod_installed(self, slug: str) -> bool:
        """Проверить, установлен ли мод"""
        mod_info = self.state_manager.get_mod(slug)
        if not mod_info:
            return False
        
        # Проверяем существование файла
        mod_file = self._get_mod_file_path(mod_info.file_name)
        return mod_file.exists()
    
    def _remove_old_mod_file(self, slug: str):
        """Удалить старый файл мода"""
        mod_info = self.state_manager.get_mod(slug)
        if mod_info:
            old_file = self._get_mod_file_path(mod_info.file_name)
            if old_file.exists():
                old_file.unlink()
                logger.info(f"Удален старый файл мода: {old_file}")
    
    async def install_mod(self, mod_slug: str, force_update: bool = False, 
                         auto_update: bool = True) -> InstallResponse:
        """Установить мод и его зависимости"""
        installed = []
        updated = []
        skipped = []
        
        try:
            async with ModrinthClient(self.settings.api_cache_ttl) as client:
                # Разрешаем зависимости
                dependencies = await client.resolve_dependencies(
                    mod_slug, self.minecraft_version, self.mod_loader
                )
                
                if not dependencies:
                    return ErrorResponse(
                        message=f"Не найдено совместимых версий для мода '{mod_slug}' с Minecraft {self.minecraft_version}"
                    )
                
                # Устанавливаем каждую зависимость
                for dep in dependencies:
                    project = dep['project']
                    version = dep['version']
                    file_info = dep['file']
                    
                    if not file_info:
                        logger.warning(f"Нет файла для скачивания: {project['slug']}")
                        continue
                    
                    slug = project['slug']
                    
                    # Проверяем, нужно ли устанавливать
                    if self._is_mod_installed(slug) and not force_update:
                        existing_mod = self.state_manager.get_mod(slug)
                        if existing_mod and existing_mod.version == version['version_number']:
                            skipped.append(slug)
                            logger.info(f"Мод {slug} уже установлен и актуален")
                            continue
                    
                    # Удаляем старую версию если есть
                    if self._is_mod_installed(slug):
                        self._remove_old_mod_file(slug)
                        updated.append(slug)
                    else:
                        installed.append(slug)
                    
                    # Скачиваем файл
                    filename = file_info['filename']
                    file_path = self._get_mod_file_path(filename)
                    
                    success = await client.download_file(file_info, str(file_path))
                    if not success:
                        raise ModManagerError(f"Не удалось скачать файл: {filename}")
                    
                    # Создаем информацию о моде
                    mod_info = ModInfo(
                        slug=slug,
                        name=project['title'],
                        version=version['version_number'],
                        file_name=filename,
                        installed_at=datetime.now(),
                        auto_update=auto_update,
                        dependencies=[d['project']['slug'] for d in dependencies if d['project']['slug'] != slug],
                        minecraft_versions=version['game_versions'],
                        mod_loader=self.mod_loader,
                        project_id=project['id'],
                        version_id=version['id'],
                        file_size=file_info.get('size', 0)
                    )
                    
                    # Сохраняем в состояние
                    self.state_manager.add_mod(mod_info)
                    
                    logger.info(f"Мод установлен: {slug} v{version['version_number']}")
                
                return InstallResponse(
                    status="success",
                    installed=installed,
                    updated=updated,
                    skipped=skipped
                )
                
        except ModrinthAPIError as e:
            logger.error(f"Ошибка API при установке мода: {e}")
            return ErrorResponse(message=str(e))
        except Exception as e:
            logger.error(f"Ошибка установки мода: {e}")
            return ErrorResponse(message=f"Ошибка установки: {e}")
    
    async def update_mod(self, slug: str) -> bool:
        """Обновить конкретный мод"""
        mod_info = self.state_manager.get_mod(slug)
        if not mod_info:
            logger.warning(f"Мод не найден в состоянии: {slug}")
            return False
        
        try:
            async with ModrinthClient(self.settings.api_cache_ttl) as client:
                # Получаем последние версии
                versions = await client.get_project_versions(
                    slug,
                    game_versions=[self.minecraft_version],
                    loaders=[self.mod_loader.value]
                )
                
                compatible_versions = client.filter_compatible_versions(
                    versions, self.minecraft_version, self.mod_loader
                )
                
                if not compatible_versions:
                    logger.warning(f"Нет совместимых версий для обновления: {slug}")
                    return False
                
                latest_version = compatible_versions[0]
                
                # Проверяем, нужно ли обновление
                if latest_version['version_number'] == mod_info.version:
                    logger.info(f"Мод {slug} уже актуален")
                    return False
                
                # Обновляем мод
                response = await self.install_mod(slug, force_update=True, auto_update=mod_info.auto_update)
                return response.status == "success"
                
        except Exception as e:
            logger.error(f"Ошибка обновления мода {slug}: {e}")
            return False
    
    def remove_mod(self, slug: str) -> bool:
        """Удалить мод"""
        try:
            mod_info = self.state_manager.get_mod(slug)
            if not mod_info:
                logger.warning(f"Мод не найден: {slug}")
                return False
            
            # Удаляем файл
            mod_file = self._get_mod_file_path(mod_info.file_name)
            if mod_file.exists():
                mod_file.unlink()
                logger.info(f"Файл мода удален: {mod_file}")
            
            # Удаляем из состояния
            self.state_manager.remove_mod(slug)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления мода {slug}: {e}")
            return False
    
    def get_installed_mods(self) -> List[ModInfo]:
        """Получить список установленных модов"""
        return self.state_manager.get_all_mods()
    
    def get_server_info(self) -> Dict:
        """Получить информацию о сервере"""
        mods = self.get_installed_mods()
        
        return {
            'minecraft_version': self.minecraft_version,
            'mod_loader': self.mod_loader.value,
            'server_path': str(self.settings.minecraft_root_path),
            'mods_count': len(mods),
            'auto_update_enabled': self.settings.enable_auto_update,
            'last_update_check': self.state_manager._state['metadata'].get('last_update_check')
        }