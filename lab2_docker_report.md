# Лабораторная работа №2 «Docker»

**Цель:** изучить контейнеризацию Docker: сборку образов, запуск контейнеров, проброс портов, тома, сети, `.dockerignore`, на примере контейнеризации Django-проекта **crm**. БД проекта переведена с SQLite на PostgreSQL.

## Архитектура

```
 браузер ──:8000──▶ [web: crm-web (Django + gunicorn)] ──crm-net──▶ [db: postgres:17-alpine]
                                                                        │
                                                                   том pgdata
```

| Понятие из практикума | Где применено |
|---|---|
| Сборка образа (`Dockerfile`, ЛР 3–4) | [Dockerfile](Dockerfile): `python:3.12-slim`, зависимости ставятся отдельным слоем, затем копируется код |
| Игнорирование файлов при сборке (ЛР 6) | [.dockerignore](.dockerignore): `.git`, `__pycache__`, `db.sqlite3`, `.env` и т.д. |
| Проброс портов `-p` (ЛР 1) | `8000:8000` (web), `5432:5432` (db) |
| Сеть между контейнерами (ЛР 9) | сеть `crm-net`, web обращается к БД по имени хоста `db` |
| Тома (ЛР 10) | именованный том `pgdata` → `/var/lib/postgresql/data`, данные БД переживают пересоздание контейнера |
| Переменные окружения | [.env](.env.example): логин/пароль БД, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` |

## Что изменено в проекте

- [crm/settings.py](crm/settings.py): `DATABASES` теперь PostgreSQL с параметрами из окружения. `DB_ENGINE=sqlite` включает старую SQLite-базу (нужно для переноса данных). `SECRET_KEY`, `DEBUG` и `ALLOWED_HOSTS` берутся из окружения. Добавлен WhiteNoise для раздачи статики.
- [requirements.txt](requirements.txt): Django, psycopg 3, gunicorn, whitenoise.
- [docker/entrypoint.sh](docker/entrypoint.sh): ждёт готовности PostgreSQL, выполняет `migrate` и `collectstatic`, затем запускает gunicorn.
- [docker-compose.yml](docker-compose.yml): сервисы `db` и `web`, healthcheck БД, том и сеть.
- [docker/sqlite_dump.json](docker/sqlite_dump.json): данные, выгруженные из `db.sqlite3` (21 запись).

## Ход работы

```bash
# 1. Подготовка окружения
cp .env.example .env

# 2. Сборка образа приложения
docker compose build
docker images crm-web

# 3. Выгрузка данных из старой SQLite-базы (одноразовый контейнер с DB_ENGINE=sqlite)
docker run --rm -e DB_ENGINE=sqlite -v "$(pwd -W)/db.sqlite3:/app/db.sqlite3:ro" -v "$(pwd -W)/docker:/out" crm-web python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e admin.logentry -e sessions --indent 2 -o /out/sqlite_dump.json

# 4. Запуск PostgreSQL + приложения
docker compose up -d
docker compose ps
docker compose logs web

# 5. Загрузка данных в PostgreSQL
docker compose exec web python manage.py loaddata docker/sqlite_dump.json

# 6. Проверка
docker compose exec db psql -U crm -d crm -c "\dt"
docker volume ls
docker network ls
docker inspect crm-web-1
```

Приложение: http://localhost:8000/nariad/ (а также `/customers/`, `/employees/`, `/products/` …), админка: http://localhost:8000/admin/.

Создать администратора:

```bash
docker compose exec web python manage.py createsuperuser
```

## Результаты проверки

- `docker compose ps`: `crm-db-1` в статусе healthy, `crm-web-1` в статусе Up.
- Миграции применены, создано 24 таблицы в PostgreSQL, загружено 21 объект из SQLite.
- Все 11 разделов (`/customers/`, `/accounts/`, `/departments/`, `/employees/`, `/organizations/`, `/positions/`, `/units/`, `/proxies/`, `/products/`, `/brigadiers/`, `/nariad/`) отвечают **200**, статика (`/static/css/styles.css`) раздаётся.
- Последовательности id в PostgreSQL выровнены после импорта, так что новые записи создаются без конфликтов.

## Полезные команды

```bash
docker compose stop          # остановить
docker compose down          # удалить контейнеры (том с данными остаётся)
docker compose down -v       # удалить вместе с томом БД
docker compose exec web sh   # зайти внутрь контейнера
```
