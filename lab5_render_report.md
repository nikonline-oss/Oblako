# Лабораторная работа №5 «Модель обслуживания PaaS: деплой приложения в облако»

**Цель:** познакомиться с моделью гибкой разработки ПО, развернуть приложение на PaaS-платформе, поработать с Git.

**Порядок выполнения (по заданию):**
1. Зарегистрироваться на PaaS-платформе.
2. Создать тестовое приложение на Python.
3. Задеплоить приложение.
4. Внести изменения в исходный код и снова задеплоить.
5. Ознакомиться с дополнительными возможностями платформы и Git.

**Платформа: Render.com вместо Heroku** (замена согласована с преподавателем). С 28.11.2022 у Heroku нет бесплатного тарифа, и создать приложение без привязки карты нельзя (`Error: verification_required`). Render — PaaS той же модели: деплой через Git, сборка платформой, управляемый PostgreSQL. Есть бесплатный тариф без карты.

**Приложение:** Django-проект **crm** (CRM + раздел Dropbox из ЛР4), БД — Render PostgreSQL.
**Репозиторий:** https://github.com/nikonline-oss/Oblako, ветка `init`.

## Что подготовлено в проекте

| Файл | Зачем |
|---|---|
| [render.yaml](render.yaml) | Blueprint («инфраструктура как код»): web-сервис `crm` + база `crm-db`, команды сборки и запуска, переменные окружения |
| [deploy/render_start.sh](deploy/render_start.sh) | запуск: `migrate` → загрузка данных CRM, если БД пустая → gunicorn |
| [requirements.txt](requirements.txt) | зависимости, Render ставит их при сборке |
| [.python-version](.python-version) | версия Python (3.12) |
| [crm/settings.py](crm/settings.py) | БД из `DATABASE_URL`, `SECURE_PROXY_SSL_HEADER` для https за прокси Render, `APP_VERSION` |
| [crm/views.py](crm/views.py) | `GET /`: `app_version`, коммит текущего релиза (`release`), ID инстанса Render, запрос к БД |

Как Render запускает приложение:
- **сборка** (`buildCommand`): `pip install -r requirements.txt && python manage.py collectstatic --noinput`;
- **запуск** (`startCommand`): `bash deploy/render_start.sh`. На бесплатном тарифе нет pre-deploy команд и консоли, поэтому миграции и первичная загрузка данных выполняются при старте. Данные грузятся только в пустую БД, поэтому повторные деплои их не дублируют;
- **порт**: Render передаёт порт в `$PORT`, gunicorn слушает его автоматически;
- **БД**: `DATABASE_URL` подставляется из базы `crm-db` (`fromDatabase` в `render.yaml`);
- **секрет** `DJANGO_SECRET_KEY` Render генерирует сам (`generateValue: true`).

Переменные окружения сервиса:

| Переменная | Значение |
|---|---|
| `DATABASE_URL` | из `crm-db` |
| `DJANGO_SECRET_KEY` | сгенерирован Render |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://*.onrender.com` |
| `DB_SSL` | `0` — внутренняя сеть Render, SSL не обязателен |
| `WEB_CONCURRENCY` | `2` — воркеры gunicorn (на бесплатном инстансе 512 МБ) |
| `LOAD_INITIAL_DATA` | `1` — загрузить данные CRM в пустую БД |
| `DROPBOX_APP_KEY` | задаётся вручную (ЛР4) |

## Ход работы

### 1. Регистрация
https://dashboard.render.com/register → **Sign up with GitHub** (аккаунт, где лежит репозиторий `Oblako`). Карта не нужна.

### 2–3. Деплой

1. Код уже в GitHub: `git push Oblako init`.
2. Render Dashboard → **New** → **Blueprint** → подключить GitHub → выбрать репозиторий **Oblako**.
3. Branch: **init**. Render находит `render.yaml` и показывает, что будет создано: web service `crm` и PostgreSQL `crm-db`.
4. `DROPBOX_APP_KEY` можно оставить пустым → **Apply** (или **Deploy Blueprint**).
5. Дождаться статуса **Live** у сервиса `crm` (первая сборка идёт несколько минут; ход сборки виден в **Logs**).

Результат: `https://crm-xxxx.onrender.com/`:
- `/` — JSON: `app_version: "1.0"`, `release` (коммит), `web_container` (ID инстанса), данные из БД (`nariad_count: 2`);
- `/nariad/` — CRM;
- `/dropbox/` — раздел ЛР4.

### 4. Изменение кода и повторный деплой

```bash
# в crm/settings.py: APP_VERSION = '1.1'
git add crm/settings.py
git commit -m "Версия 1.1"
git push Oblako init
```

Render замечает новый коммит в ветке `init` и сам пересобирает и перезапускает сервис (Auto-Deploy). После статуса **Live** на `/` будет `app_version: "1.1"`, а `release` сменится на новый коммит. История деплоев — вкладка **Events**.

### 5. Дополнительные возможности Render и Git

| Возможность | Где |
|---|---|
| Логи сборки и работы в реальном времени | сервис → **Logs** |
| История деплоев, ручной деплой, откат к прошлому деплою | **Events** → **Rollback**; **Manual Deploy** → *Deploy latest commit* / *Clear build cache & deploy* |
| Переменные окружения | **Environment** |
| Метрики CPU / памяти / запросов | **Metrics** |
| Свой домен с бесплатным HTTPS | **Settings** → **Custom Domains** |
| Состояние БД, строки подключения | `crm-db` → **Info** (Internal/External Database URL) |
| Подключиться к БД с компьютера | `psql <External Database URL>` |
| Отключить автодеплой | **Settings** → **Auto-Deploy** |

Git: `git log --oneline` (история), `git remote -v` (remote `Oblako` на GitHub), `git push Oblako init` (деплой — это просто push).

Ограничения бесплатного тарифа: сервис засыпает после 15 минут без запросов, и первый запрос после этого идёт ~1 минуту. Бесплатная БД удаляется через 30 дней.

## Проверка без Render (локально)

Сборка и запуск выполнены в чистом `python:3.12-slim` (без Dockerfile проекта), с пустой PostgreSQL и переменными как в `render.yaml`. Команды взяты прямо из `render.yaml`:

| Проверка | Результат |
|---|---|
| `buildCommand` | зависимости установлены, `129 static files copied` |
| `startCommand`, первый запуск | все миграции применены, `БД пустая — загружаю docker/sqlite_dump.json`, `Installed 21 object(s)` |
| gunicorn | `Listening at: http://0.0.0.0:10000`, 2 воркера (`WEB_CONCURRENCY=2`) |
| `GET /` | `release: abc1234`, `web_container: srv-crm-abcde`, `nariad_count: 2` |
| `GET /nariad/`, `/static/css/styles.css` при `DEBUG=0` | 200, 200 |
| перезапуск (= новый деплой) | `No migrations to apply`, повторной загрузки данных нет, `nariad_count: 2` |

Подготовка к Heroku ([Procfile](Procfile), [deploy/heroku.sh](deploy/heroku.sh)) тоже осталась в проекте: после верификации аккаунта Heroku деплой туда делается командой `./deploy/heroku.sh <имя> --load-data`.

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
| `$PORT` | выдаёт платформа (Render — 10000) | порт приложения на PaaS | — |

Внутренние порты (PostgreSQL 5432 внутри сети Docker, служебные порты Swarm 2377/7946/4789) порты хоста не занимают.

Перед запуском `deploy.sh` проверяет на сервере, свободны ли `WEB_PORT` и `DB_PORT` (то же вручную: `./deploy/ports.sh`). Если порт занят чужим процессом, деплой останавливается и показывает, какой именно. Порты сам он не меняет.

## Ответы на контрольные вопросы

1. **Почему Agile становится популярнее?** Результат виден после каждой короткой итерации, требования можно менять по ходу, ошибки находятся рано, заказчик постоянно вовлечён. Это снижает риск сделать «не то». PaaS с автодеплоем по `git push` хорошо поддерживает такой цикл: каждая итерация сразу доступна заказчику.
2. **Преимущества PaaS перед IaaS.** Не нужно администрировать ОС, веб-сервер, обновления, балансировку, сертификаты и БД: платформа делает это сама. Разработчик отвечает только за код и конфигурацию (`render.yaml`), деплой — это `git push`, масштабирование — одна настройка.
3. **add, commit, push.** `add` — добавить изменения в индекс (подготовить к фиксации); `commit` — зафиксировать проиндексированные изменения в локальной истории; `push` — отправить коммиты в удалённый репозиторий (здесь `push` в GitHub ещё и запускает сборку и деплой на Render).
4. **PaaS против локального окружения.** Приложение сразу доступно из интернета по https, есть готовые управляемые сервисы (PostgreSQL, логи, метрики), история деплоев с откатом, одинаковое окружение для всех разработчиков, не нужно держать включённый компьютер.
