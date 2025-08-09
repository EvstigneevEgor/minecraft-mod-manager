# Minecraft Mod Manager

Полноценный API-сервис для управления модами Minecraft через Modrinth API с поддержкой автоматических обновлений.

## Возможности

- 🔧 **Установка модов** - Автоматическая установка модов и их зависимостей
- 🔄 **Автообновления** - Периодическая проверка и установка обновлений
- 📊 **Управление зависимостями** - Рекурсивное разрешение зависимостей модов
- 🎯 **Совместимость версий** - Автоматический подбор совместимых версий
- 📝 **Логирование** - Подробные логи всех операций
- 🌐 **REST API** - Полноценный HTTP API для управления
- 🔍 **Мониторинг** - Статус сервиса и проверка здоровья системы

## Поддерживаемые загрузчики

- ✅ **Fabric** - Полная поддержка
- 🚧 **Forge** - Базовая поддержка (планируется расширение)

## Требования

- Python 3.10+
- Minecraft сервер с Fabric/Forge
- Доступ к интернету для Modrinth API

## Установка

### 1. Клонирование и настройка

```bash
# Клонируйте проект
git clone <repository-url>
cd minecraft-mod-manager

# Создайте виртуальное окружение
python -m venv venv

# Активируйте виртуальное окружение
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

### 2. Конфигурация

Скопируйте файл примера конфигурации:

```bash
cp .env.example .env
```

Отредактируйте `.env` файл под ваши нужды:

```env
# Путь к корневой папке Minecraft сервера
MINECRAFT_ROOT_PATH=/home/mc/server

# Включить автообновления
ENABLE_AUTO_UPDATE=true

# Интервал проверки обновлений в часах
UPDATE_INTERVAL=2

# Тип загрузчика модов
MOD_LOADER=fabric

# Порт для API сервера
PORT=8000
HOST=0.0.0.0
```

Или настройте [`config.json`](config.json):

```json
{
  "minecraft_root_path": "/home/mc/server",
  "enable_auto_update": true,
  "update_interval": 2,
  "mod_loader": "fabric",
  "log_level": "INFO"
}
```

### 3. Запуск

```bash
# Запуск сервера
python -m app.main

# Или с помощью uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Использование API

### Основные эндпоинты

#### Установка мода

```bash
curl -X POST "http://localhost:8000/install" \
  -H "Content-Type: application/json" \
  -d '{"mod": "sodium"}'
```

```bash
curl -X POST "http://localhost:8000/install" \
  -H "Content-Type: application/json" \
  -d '{"mod": "https://modrinth.com/mod/sodium"}'
```

#### Список установленных модов

```bash
curl "http://localhost:8000/mods"
```

#### Удаление мода

```bash
curl -X DELETE "http://localhost:8000/mods/sodium"
```

#### Обновление мода

```bash
curl -X POST "http://localhost:8000/mods/sodium/update"
```

#### Информация о сервере

```bash
curl "http://localhost:8000/server/info"
```

### Управление автообновлениями

#### Статус автообновления

```bash
curl "http://localhost:8000/auto-update/status"
```

#### Включить автообновление

```bash
curl -X POST "http://localhost:8000/auto-update/enable"
```

#### Отключить автообновление

```bash
curl -X POST "http://localhost:8000/auto-update/disable"
```

#### Запустить обновление вручную

```bash
curl -X POST "http://localhost:8000/auto-update/run"
```

#### Логи обновлений

```bash
curl "http://localhost:8000/auto-update/logs?limit=20"
```

### Проверка здоровья

```bash
curl "http://localhost:8000/health"
```

## Примеры ответов API

### Успешная установка

```json
{
  "status": "success",
  "installed": ["sodium", "fabric-api"],
  "updated": [],
  "skipped": ["cloth-config"]
}
```

### Ошибка установки

```json
{
  "status": "error",
  "message": "No compatible version found for 'lithium' with Minecraft 1.21.1"
}
```

### Список модов

```json
{
  "mods": [
    {
      "slug": "sodium",
      "name": "Sodium",
      "version": "mc1.21.1-0.6.0-fabric",
      "file_name": "sodium-fabric-0.6.0+mc1.21.1.jar",
      "installed_at": "2025-01-15T10:30:00Z",
      "auto_update": true,
      "dependencies": ["fabric-api"],
      "minecraft_versions": ["1.21.1"],
      "mod_loader": "fabric"
    }
  ],
  "total": 1,
  "minecraft_version": "1.21.1",
  "mod_loader": "fabric"
}
```

## Структура проекта

```
minecraft-mod-manager/
├── app/
│   ├── __init__.py          # Инициализация пакета
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Управление конфигурацией
│   ├── models.py            # Pydantic модели
│   ├── mod_manager.py       # Основная логика управления модами
│   ├── modrinth_api.py      # Клиент Modrinth API
│   └── updater.py           # Автообновление модов
├── config.json              # Конфигурация приложения
├── .env.example             # Пример переменных окружения
├── requirements.txt         # Python зависимости
└── README.md               # Документация
```

## Логи и состояние

Приложение создает следующие файлы в корневой папке Minecraft сервера:

- `mod_manager_state.json` - Состояние установленных модов
- `mod_manager.log` - Логи приложения
- `mod_manager_state.json.backup` - Резервная копия состояния

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MINECRAFT_ROOT_PATH` | Путь к серверу Minecraft | `/home/mc/server` |
| `ENABLE_AUTO_UPDATE` | Включить автообновления | `true` |
| `UPDATE_INTERVAL` | Интервал обновлений (часы) | `2` |
| `MOD_LOADER` | Тип загрузчика (`fabric`/`forge`) | `fabric` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `PORT` | Порт API сервера | `8000` |
| `HOST` | Хост API сервера | `0.0.0.0` |

### Определение версии Minecraft

Приложение автоматически определяет версию Minecraft сервера:

1. Из файла `server.properties` (поле `version` или `minecraft-version`)
2. Из логов сервера `logs/latest.log`

### Определение типа загрузчика

Автоматическое определение по наличию файлов:

- **Fabric**: `fabric-server-mc.*.jar`, `fabric-loader-*.jar`, `.fabric`
- **Forge**: `forge-*.jar`, `minecraft_server.*.jar`, `libraries/net/minecraftforge`

## Устранение неполадок

### Ошибки конфигурации

```bash
# Проверьте права доступа к папке сервера
ls -la /path/to/minecraft/server

# Проверьте существование папки модов
ls -la /path/to/minecraft/server/mods
```

### Проблемы с API

```bash
# Проверьте доступность Modrinth API
curl https://api.modrinth.com/v2/

# Проверьте логи приложения
tail -f /path/to/minecraft/server/mod_manager.log
```

### Проблемы с автообновлением

```bash
# Проверьте статус автообновления
curl "http://localhost:8000/auto-update/status"

# Проверьте логи обновлений
curl "http://localhost:8000/auto-update/logs"
```

## Разработка

### Запуск в режиме разработки

```bash
# С автоперезагрузкой
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# С отладочными логами
LOG_LEVEL=DEBUG python -m app.main
```

### Тестирование

```bash
# Установка тестовых зависимостей
pip install pytest pytest-asyncio httpx

# Запуск тестов
pytest tests/
```

## Лицензия

MIT License

## Поддержка

Для сообщения об ошибках и предложений создавайте issues в репозитории проекта.

## Roadmap

- [ ] Поддержка CurseForge API
- [ ] Веб-интерфейс для управления
- [ ] Docker контейнер
- [ ] Поддержка профилей модов
- [ ] Интеграция с Discord ботом
- [ ] Расширенная поддержка Forge