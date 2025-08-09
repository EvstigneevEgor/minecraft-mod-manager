"""
FastAPI приложение для управления модами Minecraft
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings, config_manager
from app.models import (
    InstallRequest, InstallResponse, ErrorResponse, ModListResponse,
    ServerInfo, AutoUpdateStatus, UpdateLogsResponse, HealthResponse,
    ModInfo
)
from app.mod_manager import ModManager, ModManagerError
from app.updater import AutoUpdater
from app.modrinth_api import ModrinthAPIError

# Настройка логирования
def setup_logging(settings: Settings):
    """Настройка системы логирования"""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие обработчики
    root_logger.handlers.clear()
    
    # Добавляем обработчик для файла
    try:
        file_handler = logging.FileHandler(settings.log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Не удалось создать файл логов: {e}")
    
    # Добавляем обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# Глобальные переменные для менеджеров
mod_manager: Optional[ModManager] = None
auto_updater: Optional[AutoUpdater] = None
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global mod_manager, auto_updater
    
    # Инициализация при запуске
    try:
        settings = get_settings()
        setup_logging(settings)
        
        logger.info("Запуск Minecraft Mod Manager")
        
        # Проверяем пути
        errors = config_manager.validate_paths(settings)
        if errors:
            for error in errors:
                logger.error(error)
            raise RuntimeError("Ошибки конфигурации путей")
        
        # Инициализируем менеджер модов
        mod_manager = ModManager(settings)
        await mod_manager.initialize()
        
        # Инициализируем автообновлятор
        auto_updater = AutoUpdater(settings, mod_manager)
        await auto_updater.start()
        
        logger.info("Приложение успешно запущено")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации приложения: {e}")
        raise
    
    yield
    
    # Очистка при завершении
    try:
        if auto_updater:
            await auto_updater.stop()
        logger.info("Приложение завершено")
    except Exception as e:
        logger.error(f"Ошибка при завершении: {e}")


# Создание FastAPI приложения
app = FastAPI(
    title="Minecraft Mod Manager",
    description="API сервис для управления модами Minecraft через Modrinth",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить конкретными доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_mod_manager() -> ModManager:
    """Получить экземпляр менеджера модов"""
    if mod_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер модов не инициализирован")
    return mod_manager


def get_auto_updater() -> AutoUpdater:
    """Получить экземпляр автообновлятора"""
    if auto_updater is None:
        raise HTTPException(status_code=503, detail="Автообновлятор не инициализирован")
    return auto_updater


# Обработчики ошибок
@app.exception_handler(ModManagerError)
async def mod_manager_error_handler(request, exc: ModManagerError):
    """Обработчик ошибок менеджера модов"""
    logger.error(f"Ошибка менеджера модов: {exc}")
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(message=str(exc)).model_dump()
    )


@app.exception_handler(ModrinthAPIError)
async def modrinth_api_error_handler(request, exc: ModrinthAPIError):
    """Обработчик ошибок Modrinth API"""
    logger.error(f"Ошибка Modrinth API: {exc}")
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(message=f"Ошибка API: {exc}").model_dump()
    )


# Основные эндпоинты
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка состояния сервиса"""
    uptime = time.time() - app_start_time
    
    # Проверяем доступность Minecraft сервера
    minecraft_accessible = False
    try:
        manager = get_mod_manager()
        minecraft_accessible = manager.settings.minecraft_root_path.exists()
    except:
        pass
    
    # Проверяем доступность Modrinth API
    modrinth_accessible = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.modrinth.com/v2/")
            modrinth_accessible = response.status_code == 200
    except:
        pass
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=uptime,
        minecraft_server_accessible=minecraft_accessible,
        modrinth_api_accessible=modrinth_accessible
    )


@app.post("/install", response_model=InstallResponse)
async def install_mod(
    request: InstallRequest,
    manager: ModManager = Depends(get_mod_manager)
):
    """Установить мод и его зависимости"""
    try:
        logger.info(f"Запрос на установку мода: {request.mod}")
        
        response = await manager.install_mod(
            request.mod,
            force_update=request.force_update,
            auto_update=request.auto_update
        )
        
        if isinstance(response, ErrorResponse):
            raise HTTPException(status_code=400, detail=response.message)
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка установки мода: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mods", response_model=ModListResponse)
async def get_installed_mods(manager: ModManager = Depends(get_mod_manager)):
    """Получить список установленных модов"""
    try:
        mods = manager.get_installed_mods()
        
        return ModListResponse(
            mods=mods,
            total=len(mods),
            minecraft_version=manager.minecraft_version,
            mod_loader=manager.mod_loader
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения списка модов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/mods/{mod_slug}")
async def remove_mod(
    mod_slug: str,
    manager: ModManager = Depends(get_mod_manager)
):
    """Удалить мод"""
    try:
        success = manager.remove_mod(mod_slug)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Мод '{mod_slug}' не найден")
        
        return {"status": "success", "message": f"Мод '{mod_slug}' удален"}
        
    except Exception as e:
        logger.error(f"Ошибка удаления мода: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mods/{mod_slug}/update")
async def update_mod(
    mod_slug: str,
    manager: ModManager = Depends(get_mod_manager)
):
    """Обновить конкретный мод"""
    try:
        success = await manager.update_mod(mod_slug)
        
        if not success:
            return {"status": "skipped", "message": f"Мод '{mod_slug}' уже актуален или не найден"}
        
        return {"status": "success", "message": f"Мод '{mod_slug}' обновлен"}
        
    except Exception as e:
        logger.error(f"Ошибка обновления мода: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/server/info", response_model=ServerInfo)
async def get_server_info(manager: ModManager = Depends(get_mod_manager)):
    """Получить информацию о сервере"""
    try:
        info = manager.get_server_info()
        
        return ServerInfo(
            minecraft_version=info['minecraft_version'],
            mod_loader=manager.mod_loader,
            server_path=info['server_path'],
            mods_count=info['mods_count'],
            auto_update_enabled=info['auto_update_enabled'],
            last_update_check=datetime.fromisoformat(info['last_update_check']) if info.get('last_update_check') else None
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о сервере: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Эндпоинты автообновления
@app.get("/auto-update/status", response_model=AutoUpdateStatus)
async def get_auto_update_status(updater: AutoUpdater = Depends(get_auto_updater)):
    """Получить статус автообновления"""
    try:
        status = updater.get_status()
        
        return AutoUpdateStatus(
            enabled=status['enabled'],
            interval_hours=status['interval_hours'],
            last_check=datetime.fromisoformat(status['last_check']) if status.get('last_check') else None,
            next_check=datetime.fromisoformat(status['next_check']) if status.get('next_check') else None,
            running=status.get('update_in_progress', False)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса автообновления: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto-update/enable")
async def enable_auto_update(updater: AutoUpdater = Depends(get_auto_updater)):
    """Включить автообновление"""
    try:
        result = await updater.enable_auto_update()
        
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка включения автообновления: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto-update/disable")
async def disable_auto_update(updater: AutoUpdater = Depends(get_auto_updater)):
    """Отключить автообновление"""
    try:
        result = await updater.disable_auto_update()
        
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка отключения автообновления: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto-update/run")
async def run_update_now(updater: AutoUpdater = Depends(get_auto_updater)):
    """Запустить проверку обновлений вручную"""
    try:
        result = await updater.run_update_now()
        
        if result['status'] == 'error':
            raise HTTPException(status_code=400, detail=result['message'])
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка запуска обновления: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auto-update/logs", response_model=UpdateLogsResponse)
async def get_update_logs(
    limit: Optional[int] = 50,
    updater: AutoUpdater = Depends(get_auto_updater)
):
    """Получить логи обновлений"""
    try:
        logs = updater.get_update_logs(limit)
        
        return UpdateLogsResponse(
            logs=logs,
            total=len(logs)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения логов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/auto-update/logs")
async def clear_update_logs(updater: AutoUpdater = Depends(get_auto_updater)):
    """Очистить логи обновлений"""
    try:
        updater.clear_update_logs()
        return {"status": "success", "message": "Логи очищены"}
        
    except Exception as e:
        logger.error(f"Ошибка очистки логов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )