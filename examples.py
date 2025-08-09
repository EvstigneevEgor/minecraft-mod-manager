#!/usr/bin/env python3
"""
Примеры использования Minecraft Mod Manager API
"""

import asyncio
import httpx
import json
from typing import Dict, Any

class ModManagerClient:
    """Простой клиент для работы с Minecraft Mod Manager API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """Выполнить HTTP запрос"""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> Dict[Any, Any]:
        """Проверка состояния сервиса"""
        return await self._request("GET", "/health")
    
    async def get_server_info(self) -> Dict[Any, Any]:
        """Получить информацию о сервере"""
        return await self._request("GET", "/server/info")
    
    async def install_mod(self, mod: str, force_update: bool = False, auto_update: bool = True) -> Dict[Any, Any]:
        """Установить мод"""
        data = {
            "mod": mod,
            "force_update": force_update,
            "auto_update": auto_update
        }
        return await self._request("POST", "/install", json=data)
    
    async def get_mods(self) -> Dict[Any, Any]:
        """Получить список установленных модов"""
        return await self._request("GET", "/mods")
    
    async def remove_mod(self, mod_slug: str) -> Dict[Any, Any]:
        """Удалить мод"""
        return await self._request("DELETE", f"/mods/{mod_slug}")
    
    async def update_mod(self, mod_slug: str) -> Dict[Any, Any]:
        """Обновить мод"""
        return await self._request("POST", f"/mods/{mod_slug}/update")
    
    async def get_auto_update_status(self) -> Dict[Any, Any]:
        """Получить статус автообновления"""
        return await self._request("GET", "/auto-update/status")
    
    async def enable_auto_update(self) -> Dict[Any, Any]:
        """Включить автообновление"""
        return await self._request("POST", "/auto-update/enable")
    
    async def disable_auto_update(self) -> Dict[Any, Any]:
        """Отключить автообновление"""
        return await self._request("POST", "/auto-update/disable")
    
    async def run_update_now(self) -> Dict[Any, Any]:
        """Запустить обновление вручную"""
        return await self._request("POST", "/auto-update/run")
    
    async def get_update_logs(self, limit: int = 50) -> Dict[Any, Any]:
        """Получить логи обновлений"""
        return await self._request("GET", f"/auto-update/logs?limit={limit}")

def print_json(data: Dict[Any, Any], title: str = ""):
    """Красиво вывести JSON"""
    if title:
        print(f"\n📋 {title}")
        print("=" * (len(title) + 4))
    print(json.dumps(data, indent=2, ensure_ascii=False))

async def example_basic_usage():
    """Пример базового использования"""
    print("🚀 Пример базового использования Minecraft Mod Manager")
    
    client = ModManagerClient()
    
    try:
        # 1. Проверка состояния сервиса
        print("\n1️⃣ Проверка состояния сервиса...")
        health = await client.health_check()
        print(f"   Статус: {health['status']}")
        print(f"   Время работы: {health['uptime']:.1f}s")
        print(f"   Modrinth API: {'✅' if health['modrinth_api_accessible'] else '❌'}")
        
        # 2. Информация о сервере
        print("\n2️⃣ Получение информации о сервере...")
        server_info = await client.get_server_info()
        print(f"   Minecraft: {server_info['minecraft_version']}")
        print(f"   Загрузчик: {server_info['mod_loader']}")
        print(f"   Установлено модов: {server_info['mods_count']}")
        
        # 3. Список установленных модов
        print("\n3️⃣ Список установленных модов...")
        mods = await client.get_mods()
        print(f"   Всего модов: {mods['total']}")
        
        if mods['mods']:
            print("   Установленные моды:")
            for mod in mods['mods'][:5]:  # Показываем первые 5
                print(f"   - {mod['name']} v{mod['version']}")
        
        # 4. Статус автообновления
        print("\n4️⃣ Статус автообновления...")
        auto_status = await client.get_auto_update_status()
        print(f"   Включено: {'✅' if auto_status['enabled'] else '❌'}")
        print(f"   Интервал: {auto_status['interval_hours']} ч.")
        if auto_status.get('last_check'):
            print(f"   Последняя проверка: {auto_status['last_check']}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

async def example_install_popular_mods():
    """Пример установки популярных модов"""
    print("\n🔧 Пример установки популярных модов")
    
    client = ModManagerClient()
    
    # Список популярных модов для Fabric
    popular_mods = [
        "sodium",           # Оптимизация рендеринга
        "lithium",          # Оптимизация сервера
        "phosphor",         # Оптимизация освещения
        "iris",             # Шейдеры
        "modmenu",          # Меню модов
    ]
    
    for i, mod in enumerate(popular_mods, 1):
        try:
            print(f"\n{i}️⃣ Установка мода: {mod}")
            result = await client.install_mod(mod)
            
            if result['status'] == 'success':
                print(f"   ✅ Успешно установлено:")
                for installed in result['installed']:
                    print(f"      + {installed}")
                for updated in result['updated']:
                    print(f"      ↗️ {updated} (обновлен)")
                for skipped in result['skipped']:
                    print(f"      ⏭️ {skipped} (пропущен)")
            else:
                print(f"   ❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")
                
        except Exception as e:
            print(f"   ❌ Ошибка установки {mod}: {e}")
        
        # Небольшая пауза между установками
        await asyncio.sleep(1)

async def example_mod_management():
    """Пример управления модами"""
    print("\n🔄 Пример управления модами")
    
    client = ModManagerClient()
    
    try:
        # Получаем список модов
        mods = await client.get_mods()
        
        if not mods['mods']:
            print("   Нет установленных модов для демонстрации")
            return
        
        # Берем первый мод для примера
        example_mod = mods['mods'][0]
        mod_slug = example_mod['slug']
        
        print(f"   Работаем с модом: {example_mod['name']} ({mod_slug})")
        
        # 1. Обновление мода
        print(f"\n1️⃣ Попытка обновления мода {mod_slug}...")
        update_result = await client.update_mod(mod_slug)
        print(f"   Результат: {update_result['status']} - {update_result['message']}")
        
        # 2. Получение обновленной информации
        print(f"\n2️⃣ Получение обновленной информации...")
        updated_mods = await client.get_mods()
        updated_mod = next((m for m in updated_mods['mods'] if m['slug'] == mod_slug), None)
        
        if updated_mod:
            print(f"   Текущая версия: {updated_mod['version']}")
            print(f"   Автообновление: {'✅' if updated_mod['auto_update'] else '❌'}")
        
        # 3. Демонстрация удаления (закомментировано для безопасности)
        print(f"\n3️⃣ Удаление мода (демонстрация - закомментировано)")
        print(f"   # await client.remove_mod('{mod_slug}')")
        print(f"   # print('Мод {mod_slug} удален')")
        
    except Exception as e:
        print(f"❌ Ошибка управления модами: {e}")

async def example_auto_update_management():
    """Пример управления автообновлениями"""
    print("\n⚙️ Пример управления автообновлениями")
    
    client = ModManagerClient()
    
    try:
        # 1. Получаем текущий статус
        print("\n1️⃣ Текущий статус автообновления...")
        status = await client.get_auto_update_status()
        print_json(status, "Статус автообновления")
        
        # 2. Получаем логи обновлений
        print("\n2️⃣ Последние логи обновлений...")
        logs = await client.get_update_logs(limit=10)
        
        if logs['logs']:
            print(f"   Найдено {logs['total']} записей в логах:")
            for log in logs['logs'][:5]:  # Показываем первые 5
                print(f"   - {log['timestamp']}: {log['mod_slug']} "
                      f"{log['old_version']} -> {log['new_version']} ({log['status']})")
        else:
            print("   Логи обновлений пусты")
        
        # 3. Запуск обновления вручную
        print("\n3️⃣ Запуск проверки обновлений вручную...")
        run_result = await client.run_update_now()
        print(f"   Результат: {run_result['status']} - {run_result['message']}")
        
        # 4. Демонстрация включения/отключения (осторожно)
        print("\n4️⃣ Управление автообновлением (демонстрация)")
        
        if status['enabled']:
            print("   Автообновление включено")
            print("   # await client.disable_auto_update()  # Отключить")
            print("   # await client.enable_auto_update()   # Включить обратно")
        else:
            print("   Автообновление отключено")
            print("   # await client.enable_auto_update()   # Включить")
        
    except Exception as e:
        print(f"❌ Ошибка управления автообновлениями: {e}")

async def example_error_handling():
    """Пример обработки ошибок"""
    print("\n🚨 Пример обработки ошибок")
    
    client = ModManagerClient()
    
    # 1. Попытка установить несуществующий мод
    print("\n1️⃣ Попытка установить несуществующий мод...")
    try:
        result = await client.install_mod("nonexistent-mod-12345")
        print(f"   Неожиданный успех: {result}")
    except httpx.HTTPStatusError as e:
        print(f"   ✅ Ожидаемая ошибка HTTP {e.response.status_code}")
        try:
            error_data = e.response.json()
            print(f"   Сообщение: {error_data.get('message', 'Нет сообщения')}")
        except:
            print(f"   Текст ошибки: {e.response.text}")
    except Exception as e:
        print(f"   ❌ Неожиданная ошибка: {e}")
    
    # 2. Попытка удалить несуществующий мод
    print("\n2️⃣ Попытка удалить несуществующий мод...")
    try:
        result = await client.remove_mod("nonexistent-mod-12345")
        print(f"   Неожиданный успех: {result}")
    except httpx.HTTPStatusError as e:
        print(f"   ✅ Ожидаемая ошибка HTTP {e.response.status_code}")
    except Exception as e:
        print(f"   ❌ Неожиданная ошибка: {e}")
    
    # 3. Проверка недоступного сервера
    print("\n3️⃣ Проверка недоступного сервера...")
    offline_client = ModManagerClient("http://localhost:9999")  # Неправильный порт
    
    try:
        result = await offline_client.health_check()
        print(f"   Неожиданный успех: {result}")
    except httpx.ConnectError:
        print("   ✅ Ожидаемая ошибка подключения")
    except Exception as e:
        print(f"   ❌ Неожиданная ошибка: {e}")

async def main():
    """Главная функция с примерами"""
    print("📚 Примеры использования Minecraft Mod Manager API")
    print("=" * 50)
    
    print("\n⚠️  Убедитесь, что сервер запущен: python run.py")
    print("   Нажмите Enter для продолжения или Ctrl+C для отмены...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n👋 Отменено пользователем")
        return
    
    # Запускаем примеры
    await example_basic_usage()
    await asyncio.sleep(2)
    
    await example_auto_update_management()
    await asyncio.sleep(2)
    
    await example_error_handling()
    await asyncio.sleep(2)
    
    # Спрашиваем про установку модов
    print("\n" + "=" * 50)
    print("🤔 Хотите запустить пример установки популярных модов?")
    print("   Это установит несколько модов в ваш Minecraft сервер.")
    print("   Введите 'yes' для продолжения или любой другой текст для пропуска:")
    
    try:
        response = input().strip().lower()
        if response == 'yes':
            await example_install_popular_mods()
            await asyncio.sleep(2)
            await example_mod_management()
        else:
            print("   ⏭️ Установка модов пропущена")
    except KeyboardInterrupt:
        print("\n👋 Отменено пользователем")
    
    print("\n" + "=" * 50)
    print("✅ Все примеры завершены!")
    print("📖 Больше информации в README.md")

if __name__ == "__main__":
    asyncio.run(main())