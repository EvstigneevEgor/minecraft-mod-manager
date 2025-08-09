#!/usr/bin/env python3
"""
Базовые тесты для проверки функциональности Minecraft Mod Manager
"""

import asyncio
import json
import tempfile
from pathlib import Path
import httpx
import sys

async def test_api_endpoints():
    """Тестирование API эндпоинтов"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔍 Тестирование API эндпоинтов...")
        
        # Тест health check
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Health check: {health['status']}")
                print(f"   Uptime: {health['uptime']:.1f}s")
                print(f"   Modrinth API: {'✅' if health['modrinth_api_accessible'] else '❌'}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
        
        # Тест получения информации о сервере
        try:
            response = await client.get(f"{base_url}/server/info")
            if response.status_code == 200:
                info = response.json()
                print(f"✅ Server info: Minecraft {info['minecraft_version']}, {info['mod_loader']}")
                print(f"   Установлено модов: {info['mods_count']}")
            else:
                print(f"❌ Server info failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Server info error: {e}")
        
        # Тест получения списка модов
        try:
            response = await client.get(f"{base_url}/mods")
            if response.status_code == 200:
                mods = response.json()
                print(f"✅ Mods list: {mods['total']} модов")
            else:
                print(f"❌ Mods list failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Mods list error: {e}")
        
        # Тест статуса автообновления
        try:
            response = await client.get(f"{base_url}/auto-update/status")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Auto-update status: {'включено' if status['enabled'] else 'отключено'}")
            else:
                print(f"❌ Auto-update status failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Auto-update status error: {e}")
        
        return True

def test_configuration():
    """Тестирование конфигурации"""
    print("🔧 Тестирование конфигурации...")
    
    try:
        from app.config import get_settings, config_manager
        
        settings = get_settings()
        print(f"✅ Конфигурация загружена")
        print(f"   Minecraft path: {settings.minecraft_root_path}")
        print(f"   Mod loader: {settings.mod_loader}")
        print(f"   Auto update: {settings.enable_auto_update}")
        
        # Проверяем пути
        errors = config_manager.validate_paths(settings)
        if errors:
            print("⚠️  Предупреждения конфигурации:")
            for error in errors:
                print(f"   - {error}")
        else:
            print("✅ Все пути корректны")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

async def test_modrinth_api():
    """Тестирование Modrinth API"""
    print("🌐 Тестирование Modrinth API...")
    
    try:
        from app.modrinth_api import ModrinthClient
        
        async with ModrinthClient() as client:
            # Тест получения проекта
            project = await client.get_project("sodium")
            print(f"✅ Получен проект: {project['title']}")
            
            # Тест получения версий
            versions = await client.get_project_versions("sodium")
            print(f"✅ Получено версий: {len(versions)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка Modrinth API: {e}")
        return False

def create_test_minecraft_server():
    """Создать тестовый Minecraft сервер"""
    print("🏗️  Создание тестового Minecraft сервера...")
    
    # Создаем временную папку
    test_dir = Path(tempfile.mkdtemp(prefix="minecraft_test_"))
    print(f"   Тестовая папка: {test_dir}")
    
    # Создаем структуру папок
    (test_dir / "mods").mkdir()
    (test_dir / "logs").mkdir()
    
    # Создаем server.properties
    server_properties = test_dir / "server.properties"
    server_properties.write_text("minecraft-version=1.21.1\nserver-port=25565\n")
    
    # Создаем latest.log
    latest_log = test_dir / "logs" / "latest.log"
    latest_log.write_text("[INFO] Starting minecraft server version 1.21.1\n")
    
    # Создаем fabric файл для определения загрузчика
    (test_dir / "fabric-server-mc.1.21.1.jar").touch()
    
    print(f"✅ Тестовый сервер создан: {test_dir}")
    return test_dir

def update_config_for_test(test_dir: Path):
    """Обновить конфигурацию для тестирования"""
    print("⚙️  Обновление конфигурации для тестирования...")
    
    # Обновляем config.json
    config_file = Path("config.json")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Создаем резервную копию
    if config_file.exists():
        backup_file = Path("config.json.backup")
        config_file.rename(backup_file)
        print(f"   Создана резервная копия: {backup_file}")
    
    # Обновляем путь к тестовому серверу
    config["minecraft_root_path"] = str(test_dir)
    config["enable_auto_update"] = False  # Отключаем для тестов
    config["log_level"] = "DEBUG"
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Конфигурация обновлена для тестирования")
    return backup_file

def restore_config(backup_file: Path):
    """Восстановить оригинальную конфигурацию"""
    if backup_file and backup_file.exists():
        backup_file.rename("config.json")
        print("✅ Конфигурация восстановлена")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск базовых тестов Minecraft Mod Manager\n")
    
    # Тест 1: Конфигурация
    if not test_configuration():
        print("❌ Тесты конфигурации провалены")
        return False
    
    print()
    
    # Тест 2: Modrinth API
    if not await test_modrinth_api():
        print("❌ Тесты Modrinth API провалены")
        return False
    
    print()
    
    # Тест 3: Создание тестового сервера
    test_server_dir = create_test_minecraft_server()
    backup_config = update_config_for_test(test_server_dir)
    
    print()
    
    # Тест 4: API эндпоинты (требует запущенного сервера)
    print("📡 Для тестирования API эндпоинтов запустите сервер:")
    print("   python run.py")
    print("   Затем в другом терминале:")
    print("   python test_basic.py --api-only")
    
    # Восстанавливаем конфигурацию
    restore_config(backup_config)
    
    # Удаляем тестовую папку
    import shutil
    shutil.rmtree(test_server_dir)
    print(f"🧹 Тестовая папка удалена: {test_server_dir}")
    
    print("\n✅ Базовые тесты завершены успешно!")
    return True

async def test_api_only():
    """Тестирование только API (для запущенного сервера)"""
    print("📡 Тестирование API эндпоинтов...\n")
    
    success = await test_api_endpoints()
    
    if success:
        print("\n✅ API тесты завершены успешно!")
    else:
        print("\n❌ API тесты провалены!")
    
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--api-only":
        success = asyncio.run(test_api_only())
    else:
        success = asyncio.run(main())
    
    sys.exit(0 if success else 1)