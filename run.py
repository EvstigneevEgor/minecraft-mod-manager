#!/usr/bin/env python3
"""
Скрипт запуска Minecraft Mod Manager
"""

import argparse
import asyncio
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Minecraft Mod Manager')
    parser.add_argument('--config', '-c', default='config.json', 
                       help='Путь к файлу конфигурации')
    parser.add_argument('--host', default=None, 
                       help='Хост для запуска сервера')
    parser.add_argument('--port', type=int, default=None, 
                       help='Порт для запуска сервера')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default=None, help='Уровень логирования')
    parser.add_argument('--validate-config', action='store_true', 
                       help='Только проверить конфигурацию')
    
    args = parser.parse_args()
    
    # Проверяем существование файла конфигурации
    if not Path(args.config).exists() and args.config != 'config.json':
        print(f"Ошибка: Файл конфигурации не найден: {args.config}")
        sys.exit(1)
    
    # Устанавливаем переменные окружения если переданы аргументы
    import os
    if args.host:
        os.environ['HOST'] = args.host
    if args.port:
        os.environ['PORT'] = str(args.port)
    if args.log_level:
        os.environ['LOG_LEVEL'] = args.log_level
    
    # Импортируем после установки переменных окружения
    from app.config import get_settings, config_manager
    
    try:
        settings = get_settings()
        
        # Проверяем конфигурацию
        errors = config_manager.validate_paths(settings)
        if errors:
            print("Ошибки конфигурации:")
            for error in errors:
                print(f"  - {error}")
            
            if args.validate_config:
                sys.exit(1)
            
            print("\nПродолжить несмотря на ошибки? (y/N): ", end='')
            if input().lower() != 'y':
                sys.exit(1)
        
        if args.validate_config:
            print("Конфигурация корректна!")
            print(f"Minecraft сервер: {settings.minecraft_root_path}")
            print(f"Папка модов: {settings.mods_path}")
            print(f"Автообновления: {'включены' if settings.enable_auto_update else 'отключены'}")
            print(f"Интервал обновлений: {settings.update_interval} ч.")
            return
        
        # Запускаем сервер
        print(f"Запуск Minecraft Mod Manager на {settings.host}:{settings.port}")
        print(f"Minecraft сервер: {settings.minecraft_root_path}")
        print(f"Автообновления: {'включены' if settings.enable_auto_update else 'отключены'}")
        print("Для остановки нажмите Ctrl+C")
        
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=False,
            log_level=settings.log_level.lower()
        )
        
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()