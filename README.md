# Mailing Service

Веб-приложение на Django для управления рассылками сообщений клиентам.

## Описание

Сервис позволяет пользователям создавать и управлять рассылками сообщений,
вести базу клиентов, настраивать расписание отправки и отслеживать статистику.

## Технологии

- Python 3.14+
- Django 6.0
- Django REST Framework
- PostgreSQL
- django-crontab

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-username/mailing-service.git
cd mailing-service
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактировать .env - указать свои настройки БД и SECRET_KEY
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Запустить сервер

```bash
python manage.py runserver
```

## Структура проекта

```
mailing-service/
├── config/                 # Конфигурация Django-проекта
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── mailing/                # Приложение управления рассылками
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── apps.py
├── templates/              # HTML-шаблоны
├── static/                 # Статические файлы
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
