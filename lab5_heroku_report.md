# Лабораторная работа №5 «Модель обслуживания PaaS на примере деплоя приложения в Heroku»

**Цель:** познакомиться с моделью гибкой разработки ПО, развернуть приложение на Heroku, поработать с Git.

**Порядок выполнения (по заданию):**
1. Зарегистрироваться в Heroku.
2. Создать тестовое приложение на Python.
3. Задеплоить приложение на Heroku.
4. Внести изменения в исходный код и снова задеплоить.
5. Ознакомиться с дополнительными возможностями Heroku и Git.

**Приложение:** Django-проект **crm** (CRM + раздел Dropbox из ЛР4), БД — Heroku Postgres.

> С 28.11.2022 у Heroku нет бесплатного тарифа: для деплоя нужна привязанная карта.
> Минимум — Eco dynos (5 $/мес на все приложения) + Heroku Postgres Essential-0 (~5 $/мес).
> Для студентов есть кредиты по программе GitHub Student Developer Pack.

## Что подготовлено в проекте для Heroku

| Файл | Зачем |
|---|---|
| [Procfile](Procfile) | `web:` — запуск gunicorn; `release:` — `migrate` перед каждым релизом |
| [.python-version](.python-version) | версия Python для buildpack (3.12) |
| [requirements.txt](requirements.txt) | зависимости; добавлен `dj-database-url` |
| [crm/settings.py](crm/settings.py) | БД из `DATABASE_URL` (так её отдаёт Heroku Postgres, с SSL), `SECURE_PROXY_SSL_HEADER` для https за роутером Heroku, `APP_VERSION` |
| [crm/views.py](crm/views.py) | `GET /` показывает `app_version`, номер релиза Heroku и имя dyno (`web.1`) |
| [deploy/heroku.sh](deploy/heroku.sh) | весь деплой одной командой через Heroku CLI |

Как Heroku запускает приложение:
- **сборка:** Python buildpack ставит зависимости из `requirements.txt` и сам выполняет `collectstatic` (статику отдаёт WhiteNoise);
- **release-фаза:** `python manage.py migrate --noinput`;
- **web dyno:** `gunicorn crm.wsgi:application`. Gunicorn сам слушает порт из переменной `$PORT`, которую выдаёт Heroku.

## Ход работы

### 1. Регистрация и Heroku CLI

1. Зарегистрироваться на https://signup.heroku.com и привязать карту (Account settings → Billing).
2. Установить Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli (для Windows — установщик).
3. Войти:
   ```bash
   heroku login
   ```

### 2–3. Деплой

```bash
./deploy/heroku.sh crm-ivanov --load-data
```

(имя приложения должно быть уникальным во всём Heroku)

Что выполняет скрипт:

```bash
heroku create crm-ivanov                                     # приложение + git remote "heroku"
heroku addons:create heroku-postgresql:essential-0 --wait           # БД, задаёт DATABASE_URL
heroku config:set DJANGO_SECRET_KEY=<случайный> DJANGO_DEBUG=0 \
                  DJANGO_ALLOWED_HOSTS=.herokuapp.com \
                  DJANGO_CSRF_TRUSTED_ORIGINS='https://*.herokuapp.com'
heroku labs:enable runtime-dyno-metadata                            # номер релиза в приложении
git push heroku HEAD:main                                           # сборка и релиз
heroku run python manage.py loaddata docker/sqlite_dump.json        # данные CRM (--load-data)
```

Результат: `https://crm-ivanov-1a2b3c4d5e6f.herokuapp.com/`, где `/` показывает JSON с `app_version: "1.0"` и `heroku_release`, `/nariad/` — CRM, `/dropbox/` — раздел ЛР4.

### 4. Изменение кода и повторный деплой

```bash
# поменять версию в crm/settings.py: APP_VERSION = '1.1'
git add crm/settings.py
git commit -m "Версия 1.1"
git push heroku HEAD:main        # или снова ./deploy/heroku.sh crm-ivanov
```

На `/` теперь `app_version: "1.1"`, номер `heroku_release` увеличился (например, `v6` → `v7`).

### 5. Дополнительные возможности Heroku

```bash
heroku logs --tail                  # логи приложения в реальном времени
heroku ps                           # запущенные dyno
heroku ps:scale web=2               # горизонтальное масштабирование (не на Eco)
heroku releases                     # история релизов
heroku rollback v6                  # откат на предыдущий релиз
heroku config                       # переменные окружения
heroku run python manage.py createsuperuser
heroku pg:info                      # состояние БД
heroku pg:psql                      # консоль PostgreSQL
heroku open                         # открыть сайт в браузере
```

Git: `git log --oneline` (история), `git remote -v` (remote `heroku` рядом с `Oblako`), `git push heroku HEAD:main` (деплой — это просто push).

## Проверка без Heroku (локально)

Приложение запущено в Docker в тех же условиях, что на Heroku: БД только через `DATABASE_URL`, порт из `$PORT=9300`, `DJANGO_DEBUG=0`, команды взяты из `Procfile`:

| Проверка | Результат |
|---|---|
| `release:` (`migrate`) | `No migrations to apply` — подключение по `DATABASE_URL` работает |
| `web:` (gunicorn) | `Listening at: http://0.0.0.0:9300` — порт взят из `$PORT` |
| `GET /` | `app_version: 1.0`, `heroku_release: v7`, `web_container: web.1` |
| `GET /nariad/` | 200 |
| `GET /static/css/styles.css` при `DEBUG=0` | 200 (WhiteNoise) |
| запрос с чужим `Host` | 400 (`ALLOWED_HOSTS` работает) |

Тесты раздела Dropbox (16 шт.) после изменений тоже проходят.

## Все порты проекта

Все порты, которые проект занимает на сервере или ноутбуке, задаются переменными: их можно поставить ровно такими, какие выделены на сервере.

| Переменная | Где задаётся | Что это | По умолчанию |
|---|---|---|---|
| `WEB_PORT` | `.env` / `deploy.sh --port` | сайт CRM (docker compose) | 8000 |
| `WEB_BIND` | `.env` | интерфейс сайта (`127.0.0.1` — только локально, например за nginx) | 0.0.0.0 |
| `DB_PORT` | `.env` / `deploy.sh --db-port` | PostgreSQL снаружи | 5432 |
| `DB_BIND` | `.env` | интерфейс БД (`127.0.0.1` — только с сервера) | 127.0.0.1 |
| `APP_PORT` | `.env` | порт gunicorn внутри контейнера (менять не нужно) | 8000 |
| `SWARM_HTTP_PORT` | `.env` или окружение | сайт Swarm-фермы ЛР3 | 80 |
| `REGISTRY_PORT` | `.env` или окружение | локальный registry ЛР3 | 5000 |
| `SSH_PORT` | окружение для `deploy.sh` | SSH сервера | 22 |
| `$PORT` | выдаёт Heroku | порт приложения на Heroku | — |

Внутренние порты (PostgreSQL 5432 внутри сети Docker, служебные порты Swarm 2377/7946/4789) порты хоста не занимают.

Перед запуском `deploy.sh` проверяет на сервере, свободны ли `WEB_PORT` и `DB_PORT` (то же вручную: `./deploy/ports.sh`). Если порт занят чужим процессом, деплой останавливается и показывает, какой именно. Порты сам он не меняет.

Пример выкладки на выделенные порты:

```bash
./deploy/deploy.sh user@server --port 18080 --db-port 15432 --load-data
SWARM_HTTP_PORT=18081 REGISTRY_PORT=15000 ./swarm/cluster.sh up
```

Swarm-ферма проверена на нестандартных портах: `SWARM_HTTP_PORT=8088 REGISTRY_PORT=5055` → сайт фермы отвечает на `http://localhost:8088/`.

## Ответы на контрольные вопросы

1. **Почему Agile становится популярнее?** Результат виден после каждой короткой итерации, требования можно менять по ходу, ошибки находятся рано, заказчик постоянно вовлечён. Это снижает риск сделать «не то».
2. **Преимущества PaaS перед IaaS.** Не нужно администрировать ОС, веб-сервер, обновления, балансировку и БД: платформа делает это сама. Разработчик отвечает только за код и конфигурацию, деплой занимает одну команду, масштабирование — одну настройку.
3. **add, commit, push.** `add` — добавить изменения в индекс (подготовить к фиксации); `commit` — зафиксировать проиндексированные изменения в локальной истории; `push` — отправить коммиты в удалённый репозиторий (в Heroku `push` ещё и запускает сборку и деплой).
4. **Heroku против локального окружения.** Приложение сразу доступно из интернета по https, есть готовые управляемые сервисы (Postgres, логи, метрики), релизы с откатом, масштабирование dyno, одинаковое окружение для всех разработчиков, не нужно держать включённый компьютер.
