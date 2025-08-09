"""
Pydantic модели для API запросов и ответов
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ModLoader(str, Enum):
    """Типы загрузчиков модов"""
    FABRIC = "fabric"
    FORGE = "forge"


class VersionType(str, Enum):
    """Типы версий модов"""
    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"


class InstallRequest(BaseModel):
    """Запрос на установку мода"""
    mod: str = Field(..., description="Название мода или ссылка на Modrinth")
    force_update: bool = Field(False, description="Принудительно обновить если уже установлен")
    auto_update: bool = Field(True, description="Включить автообновление для этого мода")


class ModInfo(BaseModel):
    """Информация об установленном моде"""
    slug: str
    name: str
    version: str
    file_name: str
    installed_at: datetime
    auto_update: bool
    dependencies: List[str]
    minecraft_versions: List[str]
    mod_loader: ModLoader
    project_id: str
    version_id: str
    file_size: int


class InstallResponse(BaseModel):
    """Ответ на запрос установки"""
    status: str
    installed: List[str] = Field(default_factory=list)
    updated: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    status: str = "error"
    message: str
    details: Optional[Dict[str, Any]] = None


class ModListResponse(BaseModel):
    """Список установленных модов"""
    mods: List[ModInfo]
    total: int
    minecraft_version: Optional[str] = None
    mod_loader: ModLoader


class ServerInfo(BaseModel):
    """Информация о сервере"""
    minecraft_version: str
    mod_loader: ModLoader
    server_path: str
    mods_count: int
    auto_update_enabled: bool
    last_update_check: Optional[datetime] = None


class AutoUpdateStatus(BaseModel):
    """Статус автообновления"""
    enabled: bool
    interval_hours: int
    last_check: Optional[datetime] = None
    next_check: Optional[datetime] = None
    running: bool = False


class UpdateLogEntry(BaseModel):
    """Запись лога обновлений"""
    timestamp: datetime
    mod_slug: str
    old_version: Optional[str]
    new_version: str
    status: str  # success, failed, skipped
    message: Optional[str] = None


class UpdateLogsResponse(BaseModel):
    """Логи обновлений"""
    logs: List[UpdateLogEntry]
    total: int


class HealthResponse(BaseModel):
    """Ответ проверки здоровья сервиса"""
    status: str
    version: str
    uptime: float
    minecraft_server_accessible: bool
    modrinth_api_accessible: bool