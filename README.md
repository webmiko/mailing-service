# Mailing Service

Веб-приложение на Django для управления рассылками сообщений клиентам.

## Описание

Сервис позволяет пользователям:
- Управлять базой получателей рассылки (CRUD)
- Создавать и редактировать сообщения для рассылок
- Настраивать рассылки с выбором получателей и расписания
- Отправлять рассылки вручную (через интерфейс и CLI)
- Автоматически отправлять рассылки по расписанию (django-apscheduler)
- Отслеживать попытки отправки и статистику
- Регистрироваться, входить и восстанавливать пароль
- Разграничивать доступ (пользователь/менеджер)

## Технологии

- Python 3.14+
- Django 6.0
- Django REST Framework
- PostgreSQL (psycopg2-binary)
- django-apscheduler
- python-dotenv
- Poetry
- Bootstrap 5.3 (CDN)
- Ruff (линтер/форматтер), mypy, pytest

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-username/mailing-service.git
cd mailing-service
```

### 2. Установить зависимости через Poetry

```bash
poetry install
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
```

Отредактировать `.env` — указать настройки БД, `SECRET_KEY` и email (см. раздел [Настройка email](#настройка-email-icloud-smtp)).

### 4. Создать базу данных PostgreSQL

```bash
createdb mailing_service
```

### 5. Применить миграции

```bash
poetry run python manage.py migrate
```

### 6. Создать суперпользователя

```bash
poetry run python manage.py createsuperuser
```

### 7. Запустить сервер

```bash
poetry run python manage.py runserver
```

## Структура проекта

```
mailing-service/
├── config/                     # Конфигурация Django-проекта
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── mailing/                    # Приложение управления рассылками
│   ├── models.py               # Recipient, Message, Mailing, MailingAttempt
│   ├── views.py                # CBV для CRUD, отправки, статистики
│   ├── urls.py                 # URL-маршруты
│   ├── forms.py                # Django-формы
│   ├── services.py             # Бизнес-логика отправки email
│   ├── scheduler.py            # Автоматическая отправка по расписанию
│   ├── admin.py                # Регистрация моделей в админке
│   └── management/commands/    # CLI-команда send_mailing
├── users/                      # Приложение пользователей
│   ├── models.py               # Кастомная модель User (авторизация по email)
│   ├── views.py                # Регистрация, вход, профиль, подтверждение email
│   ├── urls.py                 # URL-маршруты авторизации
│   ├── forms.py                # Формы регистрации
│   └── managers.py             # UserManager для создания пользователей
├── templates/                  # HTML-шаблоны (Bootstrap 5, адаптивная вёрстка)
├── static/                     # CSS-стили (кастомные переопределения)
├── logs/                       # Логи приложения
├── docs/                       # Документация и план проекта
├── manage.py
├── pyproject.toml
├── poetry.lock
├── requirements.txt
├── .env.example
└── .gitignore
```

## Основные команды

```bash
# Запуск сервера
poetry run python manage.py runserver

# Отправка рассылки через CLI
poetry run python manage.py send_mailing <mailing_id>

# Проверка кода
poetry run ruff check .
poetry run ruff format .

# Статический анализ типов
poetry run mypy .

# Тесты (61 тест-кейс)
poetry run pytest
# или через Django
poetry run python manage.py test
```

## Настройка email (Yandex SMTP)

Приложение использует Yandex SMTP для отправки писем. Для настройки:

1. Перейти на [id.yandex.ru/security/app-passwords](https://id.yandex.ru/security/app-passwords)
2. Войти в Яндекс ID
3. Создать пароль приложения → тип **Почта** (метка: «Mailing Service»)
4. Указать в `.env`:

```
EMAIL_HOST_USER=ваш-логин@yandex.ru
EMAIL_HOST_PASSWORD=сгенерированный-пароль
DEFAULT_FROM_EMAIL=ваш-логин@yandex.ru
```

> Обычный пароль от Яндекса не подойдёт — необходим **пароль приложения**.
> Также убедитесь, что в настройках Яндекс Почты включён доступ по IMAP/SMTP:
> [mail.yandex.ru](https://mail.yandex.ru) → Настройки → Все настройки → Почтовые программы → разрешить доступ.

## Роли пользователей

- **Пользователь** — CRUD своих клиентов и рассылок, просмотр своей статистики
- **Менеджер (is_staff)** — просмотр всех рассылок и клиентов, блокировка пользователей
