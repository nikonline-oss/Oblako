# Лабораторная работа №4 «Облачное хранилище данных Dropbox»

> Отчёт описывает ход работы на момент выполнения ЛР. Сейчас весь проект запускается одной командой `./project.sh up`: актуальные команды показа — в [LABS.md](LABS.md), выкладка на сервер — в [DEPLOY.md](DEPLOY.md).

**Задание:** создать приложение, которое работает с облачным хранилищем Dropbox через API: информация о пользователе и месте, работа с папками и файлами, подробная информация, общий доступ по ссылке и список общих ресурсов, поиск.

**Реализация:** web-приложение `cloud_storage` внутри Django-проекта **crm**, раздел **/dropbox/** (ссылка «Dropbox» в верхнем меню). Используется официальный Python SDK `dropbox` 12.0.2.

## Соответствие требованиям

| Требование | Где в интерфейсе | Метод Dropbox API |
|---|---|---|
| 2a. Подробная информация о пользователе | «Аккаунт» | `users_get_current_account` |
| 2b. Свободное/занятое место | «Файлы» (шкала) и «Аккаунт» (таблица) | `users_get_space_usage` |
| 2c. Папки: создать | «Файлы» → «Создать» | `files_create_folder_v2` |
| 2c. Папки: просмотреть | «Файлы», переход по папкам, «хлебные крошки» | `files_list_folder`, `files_list_folder_continue` |
| 2c. Папки: переместить | ⓘ → «Переместить» | `files_move_v2` |
| 2c. Папки: удалить | 🗑 | `files_delete_v2` |
| 2d. Файлы: загрузить | «Файлы» → «Загрузить» (можно несколько файлов, большие файлы грузятся частями) | `files_upload`, `files_upload_session_*` |
| 2d. Файлы: скачать | ⬇ (папка скачивается как ZIP) | `files_download`, `files_download_zip` |
| 2d. Файлы: заменить | галочка «Заменить существующие» при загрузке (без неё — сообщение о конфликте) | `files_upload(mode=overwrite)` |
| 2d. Файлы: копировать / переместить / удалить | ⓘ → «Копировать» / «Переместить» (можно задать новое имя); 🗑 | `files_copy_v2`, `files_move_v2`, `files_delete_v2` |
| 2e. Подробная информация о файле/папке | ⓘ: ID, путь, размер, даты, ревизия, content hash, ссылки | `files_get_metadata` |
| 3. Поделиться по ссылке | кнопка «Поделиться» (если ссылка уже есть — показывается она) | `sharing_create_shared_link_with_settings` |
| 3. Список общих ресурсов | «Общие ссылки» (+ отключение ссылки) | `sharing_list_shared_links`, `sharing_revoke_shared_link` |
| 4. Поиск по имени и содержимому | строка поиска; галочка «Искать и в содержимом», ограничение по папке | `files_search_v2` |

## Подключение к Dropbox

1. Создать приложение на https://www.dropbox.com/developers/apps: **Scoped access**, **Full Dropbox**.
2. На вкладке **Permissions** включить `account_info.read`, `files.metadata.read`, `files.metadata.write`, `files.content.read`, `files.content.write`, `sharing.read`, `sharing.write` и нажать **Submit**.
3. Скопировать **App key** в `.env`: `DROPBOX_APP_KEY=...`, затем выполнить `docker compose up -d`.
4. В CRM открыть **Dropbox → Подключение**, нажать «Открыть страницу разрешения Dropbox», разрешить доступ, вставить полученный код и нажать «Подключить».

Используется OAuth 2 с PKCE и `token_access_type=offline`: в БД (модель `DropboxCredential`) сохраняется refresh-токен, SDK сам обновляет короткоживущий access-токен. Поэтому подключение не «протухает» через 4 часа, а App secret хранить не нужно. Как альтернатива токен можно задать в `.env` (`DROPBOX_REFRESH_TOKEN` или `DROPBOX_ACCESS_TOKEN`).

## Развёртывание на удалённом сервере

На сервере (Ubuntu/Debian) нужен только Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER
```

Выкладка выполняется с локального компьютера (Git Bash) одной командой:

```bash
./deploy/deploy.sh user@1.2.3.4 --port 80 --load-data
```

Что делает [deploy/deploy.sh](deploy/deploy.sh):
1. проверяет, что на сервере есть `docker compose`;
2. копирует проект по SSH в `~/crm` (все файлы репозитория, без `.git`, `.env` и мусора);
3. кладёт на сервер `.env`: берёт локальный `.env.server`, если он есть, иначе оставляет существующий на сервере, иначе создаёт из `.env.example`;
4. выполняет `docker compose up -d --build --wait`, то есть ждёт, пока база и сайт станут healthy;
5. с флагом `--load-data` загружает данные CRM из `docker/sqlite_dump.json` (нужно только при первом запуске);
6. выводит адрес сайта.

Опции: `--port N` (порт сайта), `--db-port N` (порт PostgreSQL), `--dir DIR` (каталог на сервере); переменные `SSH_PORT`, `SSH_OPTS="-i ключ"`, `ENV_FILE`.

### Смена портов

Все порты — в `.env` (см. [.env.example](.env.example)):

| Переменная | Что это | По умолчанию |
|---|---|---|
| `WEB_PORT` | порт сайта снаружи | 8000 |
| `DB_PORT` | порт PostgreSQL снаружи | 5432 |
| `DB_BIND` | на каком интерфейсе открыть БД (`127.0.0.1` — только с сервера) | 127.0.0.1 |

Поменять порт можно тремя способами:
- `./deploy/deploy.sh user@host --port 8080` — с локального компьютера;
- на сервере: изменить `WEB_PORT` в `~/crm/.env`, затем `docker compose up -d`;
- держать настройки сервера в локальном `.env.server` (он в `.gitignore`) — он копируется при каждом деплое.

Внутри контейнера приложение всегда слушает порт 8000, меняется только внешний порт. Данные БД хранятся в томе `pgdata` и при смене порта или передеплое не теряются.

Для доступа по IP/домену на сервере нужно прописать его в `DJANGO_ALLOWED_HOSTS` (например, `DJANGO_ALLOWED_HOSTS=1.2.3.4,crm.example.com`), для https — в `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Проверка

**Автотесты** ([cloud_storage/tests.py](cloud_storage/tests.py)), Dropbox API подменён моком — 16 тестов, все проходят:

```bash
docker compose exec web python manage.py test cloud_storage
# Ran 16 tests ... OK
```

Покрыто: редирект на подключение без токена, просмотр папки (папки идут первыми, расчёт места), аккаунт, метаданные, создание папки, загрузка с конфликтом и с заменой, перемещение и копирование, удаление, создание и повторное создание ссылки, список ссылок, поиск по содержимому, скачивание, вывод ошибок API, страница подключения.

**Деплой** проверен на тестовом сервере (контейнер с SSH и Docker, имитирующий VPS):
- `./deploy/deploy.sh root@host --port 9090 --load-data`: контейнеры healthy, загружено 21 объект, `/nariad/`, `/dropbox/connect/` и `/` отвечают 200;
- повторный `./deploy/deploy.sh root@host --port 8085 --db-port 15432`: сайт переехал на 8085, БД на 15432, данные сохранились.

**Смена порта локально:** `WEB_PORT=8080` в `.env` → `docker compose up -d` → сайт отвечает на 8080, на 8000 больше не отвечает.

## Новые и изменённые файлы

- `cloud_storage/` — приложение (views, client, модель токена, шаблоны, тесты)
- `deploy/deploy.sh` — выкладка на сервер
- `docker-compose.yml` — порты из `.env`, healthcheck web, БД по умолчанию только на 127.0.0.1
- `.env.example` — порты, `DJANGO_CSRF_TRUSTED_ORIGINS`, переменные Dropbox
- `Dockerfile` — настройки gunicorn через `GUNICORN_CMD_ARGS`, таймаут 300 с для больших файлов
- `crm/settings.py`, `crm/urls.py`, `templates/includes/_navbar.html` — подключение раздела
- `swarm/docker-stack.yml` — порт тоже настраивается: `WEB_PORT` (по умолчанию 80)
