# Проект Foodgram
Ссылка на проект:
https://erikfoodgram.zapto.org
Описание:
Foodgram — это удобное веб-приложение, где пользователи могут публиковать кулинарные рецепты, подписываться на других кулинаров, добавлять рецепты в избранное и формировать список покупок.

## Используемые технологии
Backend: Python, Django, Django REST Framework

Frontend: React

База данных: PostgreSQL

Docker, Docker Compose

Nginx, Gunicorn

CI/CD: GitHub Actions

## Установка и запуск
### Запуск на удалённом сервере
1. Скопируйте docker-compose.production.yml на сервер.
2. Подключитесь к серверу и запустите контейнеры:
```
sudo docker compose -f docker-compose.production.yml up -d
```
3. Выполните миграции и соберите статику:
```
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

## Запуск локально (Docker)
1. Клонируйте репозиторий:
```
git clone git@github.com:example/foodgram.git
cd foodgram
```
2. Запустите контейнеры:
```
docker compose up -d
```
3. Выполните миграции и соберите статику:
```
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py collectstatic
docker compose exec backend cp -r /app/collected_static/. /backend_static/static/
```
4. Проект будет доступен по адресу http://127.0.0.1:8000/

## Автор проекта
Артем Попов
Email: butterwithbutter@mail.com