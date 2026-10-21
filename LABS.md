# Инструкция по лабораторным работам (ЛР2–ЛР7)

Все лабы — один проект. Запуск всего сразу:

```bash
./project.sh up
```

Команда сама создаст `.env` (пароли генерируются), проверит порты, соберёт и запустит контейнеры, наполнит WordPress и выведет адреса. На Windows запускайте в **Git Bash**, перед этим должен быть запущен Docker Desktop.

| ЛР | Что | Адрес (по умолчанию) |
|---|---|---|
| 2 | CRM в Docker (Django + PostgreSQL) | http://localhost:8000/nariad/ |
| 3 | Docker Swarm: узел БД + 3 реплики | http://localhost/ после `./project.sh swarm up` |
| 4 | Dropbox API в CRM | http://localhost:8000/dropbox/ |
| 5 | PaaS: CRM на Render | ссылка `https://….onrender.com` из Render Dashboard |
| 6 | MongoDB: CRUD сериалов, журнал, статистика | http://localhost:8000/journal/series/ и `./project.sh lab6` |
| 7 | WordPress (+ phpMyAdmin) | http://localhost:8081/ , http://localhost:8082/ |

Полезное:

```bash
./project.sh status      # контейнеры и адреса
./project.sh urls        # только адреса
./project.sh logs web    # логи сервиса (web, db, mongo, wordpress, wp-db, phpmyadmin)
./project.sh down        # остановить всё (данные сохраняются)
```

Логины и пароли лежат в `.env`. В git он не попадает.

---

## ЛР2. Docker

**Суть:** CRM упакована в образ (Dockerfile) и запущена вместе с PostgreSQL через docker compose; данные БД — в томе, контейнеры общаются по сети.

Что показать:

```bash
docker compose ps                          # контейнеры: web, db, mongo, wordpress, wp-db, phpmyadmin
docker images | grep crm                   # образы проекта: crm-web, crm-mongo
docker volume ls | grep crm                # тома: crm_pgdata, crm_mongodata, crm_wpdata, crm_wp-dbdata
docker network ls | grep crm               # сети: crm_crm-net, crm_wp-net
docker compose exec db psql -U crm -d crm -c "\dt"     # таблицы CRM в PostgreSQL
docker compose logs web | tail                         # migrate, collectstatic, gunicorn
docker inspect crm-web-1 | less
```

Файлы для показа: [Dockerfile](Dockerfile), [.dockerignore](.dockerignore), [docker-compose.yml](docker-compose.yml), [docker/entrypoint.sh](docker/entrypoint.sh) (ожидание БД → миграции → загрузка данных в пустую БД → gunicorn).

Открыть http://localhost:8000/nariad/ — работающая CRM.

Подробно: [lab2_docker_report.md](lab2_docker_report.md).

---

## ЛР3. Docker Swarm

**Суть:** ферма из 4 узлов Swarm (docker-in-docker): `manager` — узел БД (PostgreSQL), `worker1..3` — веб-узлы с 3 репликами CRM; порт 80; устойчивость к падению реплики и узла.

```bash
./project.sh swarm up        # ~3–5 минут: узлы, swarm init/join, метки, registry, деплой стека
./project.sh swarm status    # узлы, сервисы, где какая реплика
```

Что показать:

```bash
# 1. БД только на manager, 3 реплики web на worker-ах
docker exec manager docker node ls
docker exec manager docker service ps crm_db crm_web

# 2. Приложение на 80 порту, запрос к БД, балансировка
curl http://localhost/
for i in $(seq 1 9); do curl -s http://localhost/ | grep web_container; done | sort | uniq -c

# 3. Падение реплики: убиваем контейнер — запросы не падают, Swarm поднимает новую
docker exec worker2 sh -c 'docker rm -f $(docker ps -q --filter name=crm_web)'
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code} " http://localhost/; sleep 0.5; done; echo
docker exec manager docker service ps crm_web

# 4. Падение целого узла
docker stop worker3
docker exec manager docker node ls          # worker3 — Down, реплика переехала
docker start worker3
```

```bash
./project.sh swarm down      # удалить ферму
```

Порт сайта фермы — `SWARM_HTTP_PORT` в `.env` (по умолчанию 80, как в задании). Файлы: [swarm/docker-stack.yml](swarm/docker-stack.yml), [swarm/cluster.sh](swarm/cluster.sh).

Подробно: [lab3_swarm_report.md](lab3_swarm_report.md).

---

## ЛР4. Dropbox

**Суть:** раздел CRM для работы с Dropbox через официальный SDK.

Один раз — подключение:
1. https://www.dropbox.com/developers/apps → приложение (Scoped access, Full Dropbox); на вкладке **Permissions** включить `account_info.read`, `files.metadata.read/write`, `files.content.read/write`, `sharing.read/write` → **Submit**.
2. App key вписать в `.env`: `DROPBOX_APP_KEY=...` → `./project.sh up`.
3. http://localhost:8000/dropbox/connect/ → «Открыть страницу разрешения» → «Разрешить» → вставить код → «Подключить».

Что показать (раздел **Dropbox** в меню CRM):

| Требование | Где |
|---|---|
| Информация о пользователе | вкладка «Аккаунт» |
| Свободное/занятое место | шкала на «Файлах», таблица на «Аккаунте» |
| Папки: создать / просмотреть / переместить / удалить | «Файлы» → «Создать», переход по папкам, ⓘ → «Переместить», 🗑 |
| Файлы: загрузить / скачать / заменить / копировать / переместить / удалить | «Загрузить» (галочка «Заменить существующие»), ⬇, ⓘ → «Копировать»/«Переместить», 🗑 |
| Подробная информация | ⓘ у файла или папки |
| Общий доступ по ссылке, список ссылок | кнопка «Поделиться», вкладка «Общие ссылки» |
| Поиск по имени и содержимому | строка поиска, галочка «Искать и в содержимом» |

Подробно: [lab4_dropbox_report.md](lab4_dropbox_report.md).

---

## ЛР5. PaaS (Render вместо Heroku)

**Суть:** CRM развёрнута на PaaS по `git push`; платформа сама собирает и запускает приложение и даёт управляемый PostgreSQL.

Первый деплой (один раз): https://dashboard.render.com → **New** → **Blueprint** → репозиторий `Oblako`, ветка `init` → **Apply** (всё описано в [render.yaml](render.yaml)).

Что показать:
1. Сайт на Render: `https://crm-xxxx.onrender.com/nariad/`. Главная `/` — JSON с `app_version` и `release` (коммит).
2. Изменение и повторный деплой:
   ```bash
   # crm/settings.py: APP_VERSION = '1.1'
   git commit -am "Версия 1.1"
   git push Oblako init
   ```
   Render пересоберёт сайт сам (вкладка **Events**), на `/` будет `app_version: "1.1"` и новый `release`.
3. Возможности платформы: **Logs**, **Events** (история деплоев, Rollback), **Environment**, **Metrics**, база `crm-db` → **Info**.

Бесплатный сервис засыпает через 15 минут без запросов — откройте сайт за минуту до показа.

Подробно: [lab5_render_report.md](lab5_render_report.md).

---

## ЛР6. MongoDB

**Суть:** MongoDB 4.4, установленная по шагам методички (Ubuntu 20.04, [lab6_mongodb/ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile)); работа через Mongo Shell и PyMongo — и в учебном скрипте, и в самой CRM.

**1. Установка и Mongo Shell + PyMongo (части 1–2 методички):**

```bash
./project.sh lab6
```

Выводит по очереди: `connectionStatus` (`"ok" : 1`), CRUD в Mongo Shell над `SeriesDB.series` ([shell_demo.js](lab6_mongodb/shell_demo.js)), скрипт PyMongo ([mongo_db_script.py](lab6_mongodb/mongo_db_script.py)): insert, `DuplicateKeyError`, find, update, delete.

Интерактивно:

```bash
docker compose exec mongo mongo SeriesDB
> db.series.find({ year: 2013 })
> db.series.updateOne({ name: "Suits" }, { $set: { year: 2010 } })
```

Управление «службой» (аналог `systemctl`): `docker compose stop mongo` / `start mongo` / `restart mongo`, статус — `docker compose ps mongo`.

**2. MongoDB в CRM** — пункт **MongoDB** в меню (http://localhost:8000/journal/series/):

| Вкладка | Что показывает |
|---|---|
| **Сериалы (CRUD)** | та же коллекция `SeriesDB.series`: **создание**, **редактирование**, **удаление**, поиск по названию (`$regex`), фильтр по жанру (элемент массива) и годам, сортировка; запрос `find()` показан на странице. У каждого документа свой набор полей: жанры — массив, «Дополнительные поля» (например, «страна: США», «серий: 236») сохраняются как поля документа — схема не нужна |
| **Журнал** | каждое создание/изменение/удаление в CRM и в сериалах — документ в коллекции `crm.activity`; фильтры, полнотекстовый поиск `$text` с русской морфологией, «было → стало», исходный BSON |
| **Статистика** | агрегации `aggregate()` (`$group`, `$dateToString`), `collStats`, индексы; сами pipeline показаны на странице |

Сценарий показа: добавить сериал с доп. полями → отредактировать (поменять название, удалить поле) → удалить → открыть «Журнал» и показать три события, в карточке изменения — «было → стало».

На только что развёрнутом проекте список сериалов пуст. Его заполняет `./project.sh lab6` (сериалы из методички), или сериалы можно добавить вручную.

Подробно: [lab6_mongodb_report.md](lab6_mongodb_report.md).

---

## ЛР7. WordPress (7-1 и 7-2)

**Суть:** WordPress + MySQL + phpMyAdmin (вместо Open Server/Denwer); сайт установлен и наполнен по обеим методичкам автоматически при `./project.sh up`.

- Сайт: http://localhost:8081/
- Консоль: http://localhost:8081/wp-admin/ — `WP_ADMIN_USER` / `WP_ADMIN_PASSWORD` из `.env`
- phpMyAdmin: http://localhost:8082/ — `MYSQL_USER` / `MYSQL_PASSWORD` из `.env`

Что показать:

| Задание | Где |
|---|---|
| 7-1 I. БД и установка | phpMyAdmin → база `wptest`, таблицы `wp_*` |
| 7-1 II. Не индексировать, UTC+9, формат даты | Консоль → Настройки → Чтение / Общие |
| 7-1 III. Тема | Внешний вид → Темы (Twenty Sixteen) |
| 7-1 IV. Страницы с дочерними, картинки с alt, меню | Страницы; Медиафайлы; Внешний вид → Меню |
| 7-2 1. 3+ страницы, 2 рубрики × 3 записи, картинки/видео/таблицы/заголовки | Страницы, Записи, Рубрики; на сайте — «Рубрики» в меню |
| 7-2 2. Карта | страница «Студенту» (Яндекс.Карта) |
| 7-2 3. Форма регистрации Contact Form 7 в боковой колонке | правая колонка сайта; заявки — Консоль → Flamingo |
| 7-2 4. Шорткоды | «Портфолио» (вкладки, спойлер), «Расписание» (заметка, кнопка) |
| 7-2 5. Выпадающее меню | навести на «Портфолио», «Студенту», «Рубрики» |

Своя точка на карте: `MAP_LL=долгота,широта` в `.env`, затем `./project.sh wp-reset` (сайт соберётся заново).
Тема от преподавателя: Внешний вид → Темы → Добавить → Загрузить тему.

Подробно: [lab7_wordpress_report.md](lab7_wordpress_report.md).

---

## Порты

| Переменная `.env` | Что | По умолчанию | Нужен на сервере |
|---|---|---|---|
| `WEB_PORT` | CRM (ЛР2, 4, 6) | 8000 | да |
| `WP_PORT` | WordPress (ЛР7) | 8081 | да |
| `PMA_PORT` | phpMyAdmin (ЛР7) | 8082 | да (если показывать с компьютера — `PMA_BIND=0.0.0.0`) |
| `DB_PORT`, `MONGO_PORT` | прямой доступ к PostgreSQL и MongoDB | 5432, 27017 | нет, только при `COMPOSE_PROFILES=db-ports` |
| `SWARM_HTTP_PORT`, `REGISTRY_PORT` | Swarm-ферма ЛР3 | 80, 5000 | только если ферму показывать на сервере |

Проверить, свободны ли порты: `./deploy/ports.sh`. Выкладка на сервер — [DEPLOY.md](DEPLOY.md).
