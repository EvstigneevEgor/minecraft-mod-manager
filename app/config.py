"""
Модуль конфигурации для загрузки настроек из config.json и переменных окружения
"""

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    minecraft_root_path: str = Field(default="/home/mc/server", description="Путь к корневой папке Minecraft сервера")
    enable_auto_update: bool = Field(default=True, description="Включить автообновления")
    update_interval: int = Field(default=2, description="Интервал проверки обновлений в часах")
    server_properties_path: Optional[str] = Field(default=None, description="Путь к server.properties")
    mod_loader: str = Field(default="fabric", description="Тип загрузчика модов")
    
    # API настройки
    api_cache_ttl: int = Field(default=300, description="Время кэширования API запросов в секундах")
    max_concurrent_downloads: int = Field(default=3, description="Максимальное количество одновременных загрузок")
    download_timeout: int = Field(default=30, description="Таймаут загрузки в секундах")
    retry_attempts: int = Field(default=3, description="Количество попыток повтора при ошибке")
    
    # Настройки сервера
    host: str = Field(default="0.0.0.0", description="Хост для FastAPI сервера")
    port: int = Field(default=8000, description="Порт для FastAPI сервера")
    
    # Логирование и резервное копирование
    log_level: str = Field(default="INFO", description="Уровень логирования")
    backup_state: bool = Field(default=True, description="Создавать резервные копии состояния")
    
    # Пути к файлам
    state_file_name: str = Field(default="mod_manager_state.json", description="Имя файла состояния")
    log_file_name: str = Field(default="mod_manager.log", description="Имя файла логов")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def mods_path(self) -> Path:
        """Путь к папке модов"""
        return Path(self.minecraft_root_path) / "mods"
    
    @property
    def state_file_path(self) -> Path:
        """Путь к файлу состояния"""
        return Path(self.minecraft_root_path) / self.state_file_name
    
    @property
    def log_file_path(self) -> Path:
        """Путь к файлу логов"""
        return Path(self.minecraft_root_path) / self.log_file_name
    
    @property
    def server_properties_file_path(self) -> Path:
        """Путь к файлу server.properties"""
        if self.server_properties_path:
            return Path(self.server_properties_path)
        return Path(self.minecraft_root_path) / "server.properties"
    
    @property
    def server_logs_path(self) -> Path:
        """Путь к папке логов сервера"""
        return Path(self.minecraft_root_path) / "logs"
    
    @property
    def latest_log_path(self) -> Path:
        """Путь к последнему логу сервера"""
        return self.server_logs_path / "latest.log"


class ConfigManager:
    """Менеджер конфигурации"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self._settings: Optional[Settings] = None
    
    def load_settings(self) -> Settings:
        """Загрузить настройки из файла и переменных окружения"""
        if self._settings is not None:
            return self._settings
        
        # Загружаем настройки из config.json если он существует
        config_data = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Предупреждение: Не удалось загрузить {self.config_file}: {e}")
        
        # Создаем настройки с приоритетом переменных окружения
        self._settings = Settings(**config_data)
        return self._settings
    
    def save_settings(self, settings: Settings) -> None:
        """Сохранить настройки в файл"""
        try:
            config_data = settings.model_dump(exclude={
                'mods_path', 'state_file_path', 'log_file_path', 
                'server_properties_file_path', 'server_logs_path', 'latest_log_path'
            })
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise RuntimeError(f"Не удалось сохранить конфигурацию: {e}")
    
    def validate_paths(self, settings: Settings) -> list[str]:
        """Проверить доступность путей"""
        errors = []
        
        # Проверяем корневую папку сервера
        minecraft_path = Path(settings.minecraft_root_path)
        if not minecraft_path.exists():
            errors.append(f"Корневая папка сервера не найдена: {minecraft_path}")
        elif not minecraft_path.is_dir():
            errors.append(f"Путь не является папкой: {minecraft_path}")
        
        # Создаем папку модов если её нет
        mods_path = settings.mods_path
        if not mods_path.exists():
            try:
                mods_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(f"Не удалось создать папку модов: {e}")
        
        # Проверяем доступность для записи
        if minecraft_path.exists() and not os.access(minecraft_path, os.W_OK):
            errors.append(f"Нет прав на запись в папку сервера: {minecraft_path}")
        
        return errors


# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager()

def get_settings() -> Settings:
    """Получить настройки приложения"""
    return config_manager.load_settings()