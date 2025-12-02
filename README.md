# VK Gorb Bot

Админ-панель для управления VK рассылками.

## Структура проекта

```
vk_gorb_bot/
├── backend/          # Backend код (FastAPI)
│   ├── app.py       # Главный файл приложения
│   ├── bot.py       # Бот для консольного запуска
│   ├── config.py    # Конфигурация (читает из .env)
│   ├── storage.py   # Работа с конфигурацией
│   ├── tasks.py     # Управление задачами
│   └── vk_service.py # Сервис для работы с VK API
├── front/           # Frontend код
│   ├── templates/   # HTML шаблоны
│   └── static/      # Статические файлы (CSS, JS)
│       ├── js/      # JavaScript модули
│       └── css/     # CSS файлы
├── data/            # Данные (config.json)
├── .env             # Переменные окружения (токены и настройки)
└── requirements.txt # Зависимости Python
```

## Установка

1. Установите зависимости:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

2. Настройте `.env` файл:
```bash
# Скопируйте значения из data/config.json или создайте новый .env
USER_TOKEN=ваш_токен_пользователя
GROUP_TOKEN=ваш_токен_группы
GROUP_ID=ваш_id_группы
POST_ID=1
PROMO_MESSAGE=Ваше сообщение
REQUEST_DELAY=0.35
```

## Запуск

### Вариант 1: Использовать скрипт запуска
```bash
./run.sh
```

### Вариант 2: Запустить вручную
```bash
source venv/bin/activate
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Вариант 3: Из корня проекта
```bash
source venv/bin/activate
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

После запуска приложение будет доступно по адресу: http://localhost:8000

## Использование

1. Откройте http://localhost:8000 в браузере
2. Перейдите в "Настройки" и укажите токены VK
3. Вернитесь на главную страницу
4. Загрузите посты и выберите нужные
5. Запустите рассылку

