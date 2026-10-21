# Развёртывание CRM на удалённом сервере

CRM запускается на сервере двумя контейнерами Docker:

```
браузер ──WEB_PORT──▶ web (Django + gunicorn) ──▶ db (PostgreSQL 17, том pgdata)
                                                     └── DB_PORT (по умолчанию только 127.0.0.1)
```

Все порты и пароли задаются в файле `.env`. Ниже два способа выкладки: **А** — одной командой со своего компьютера, **Б** — вручную на сервере через `git clone`. Выберите один.

---

## 0. Что узнать у преподавателя

| Что | Пример | Куда пойдёт |
|---|---|---|
| Адрес сервера | `192.168.10.5` | `user@адрес` в командах, `DJANGO_ALLOWED_HOSTS` |
| Логин SSH (и пароль или ключ) | `student05` | `user@адрес` |
| Порт SSH, если не 22 | `2222` | `SSH_PORT` |
| **Порт для сайта** | `18080` | `WEB_PORT` |
| **Порт для БД** | `15432` | `DB_PORT` |
| Ещё порты, если на сервере нужны ЛР6/ЛР7 | 1 для MongoDB, 2 для WordPress | см. п. 7б |
| Есть ли на сервере Docker и права на него | `docker ps` работает без `sudo` | — |

Если БД снаружи не нужна, порт для неё всё равно нужен: он открыт только на `127.0.0.1` сервера, но на сервере не должен быть занят (там часто уже работает свой PostgreSQL на 5432).

Проверить доступ:

```bash
ssh -p 22 student05@192.168.10.5 "docker compose version && docker ps"
```

Если Docker нет и есть `sudo`:

```bash
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER
```

(после `usermod` выйти из SSH и зайти снова)

---

## 1. Настройки сервера: `.env.server`

В папке проекта на своём компьютере скопируйте пример:

```bash
cp .env.example .env.server
```

и поменяйте в `.env.server`:

```ini
WEB_PORT=18080                      # порт сайта, выданный преподавателем
DB_PORT=15432                       # порт БД, выданный преподавателем
DB_BIND=127.0.0.1                   # 0.0.0.0 — если БД нужна снаружи

POSTGRES_PASSWORD=придумайте_пароль
DJANGO_SECRET_KEY=длинная_случайная_строка
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=192.168.10.5   # адрес/домен сервера, через запятую

DROPBOX_APP_KEY=...                 # ЛР4, можно оставить пустым
```

Случайную строку для ключа можно получить так: `openssl rand -hex 32`.

> **Пароль БД задаётся один раз.** PostgreSQL запоминает его при первом запуске (в томе `pgdata`). Если потом поменять `POSTGRES_PASSWORD` в `.env`, сайт перестанет подключаться к БД. Поэтому придумайте пароль **до** первого деплоя.

`.env.server` не попадает в git (он в `.gitignore`), пароли в репозиторий не утекут.

---

## 2А. Выкладка одной командой (с компьютера)

Нужны: Git Bash (на Windows), доступ к серверу по SSH.

**Один раз — вход по ключу**, чтобы не вводить пароль много раз подряд:

```bash
ssh-keygen -t ed25519            # если ключа ещё нет (Enter на все вопросы)
ssh-copy-id -p 22 student05@192.168.10.5
```

Если `ssh-copy-id` нет:

```bash
cat ~/.ssh/id_ed25519.pub | ssh -p 22 student05@192.168.10.5 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Деплой** (из папки `crm`, в Git Bash):

```bash
./deploy/deploy.sh student05@192.168.10.5 --load-data
```

- `--load-data` — загрузить данные CRM (наряды, сотрудники…). Только при **первом** деплое.
- SSH не на 22 порту: `SSH_PORT=2222 ./deploy/deploy.sh ...`
- Другой ключ: `SSH_OPTS="-i ~/.ssh/my_key" ./deploy/deploy.sh ...`
- Другой каталог на сервере (по умолчанию `~/crm`): `--dir labs/crm`
- Порты можно задать прямо в команде вместо `.env.server`: `--port 18080 --db-port 15432`

Что делает скрипт:
1. проверяет, что на сервере есть `docker compose`;
2. копирует файлы проекта в `~/crm` (без `.git`, `.env`, мусора);
3. копирует `.env.server` → `~/crm/.env` (если `.env.server` нет — оставляет старый `.env` на сервере или создаёт его из `.env.example`);
4. **проверяет, свободны ли `WEB_PORT` и `DB_PORT`**. Если порт занят чужим процессом, останавливается и пишет, какой;
5. собирает образ и запускает контейнеры, ждёт, пока они станут `healthy`;
6. при `--load-data` загружает данные;
7. печатает адрес сайта.

Пример вывода в конце:

```
NAME        IMAGE                COMMAND                  SERVICE   STATUS                    PORTS
crm-db-1    postgres:17-alpine   "docker-entrypoint.s…"   db        Up 30 seconds (healthy)   127.0.0.1:15432->5432/tcp
crm-web-1   crm-web              "docker/entrypoint.s…"   web       Up 8 seconds (healthy)    0.0.0.0:18080->8000/tcp

Готово: http://192.168.10.5:18080/nariad/   Dropbox: http://192.168.10.5:18080/dropbox/
```

---

## 2Б. Выкладка вручную (на сервере)

Если со своего компьютера SSH-скрипт не работает, всё можно сделать прямо на сервере.

```bash
ssh -p 22 student05@192.168.10.5

git clone -b init https://github.com/nikonline-oss/Oblako.git crm
cd crm
cp .env.example .env
nano .env                                    # те же правки, что в п. 1

./deploy/ports.sh                            # проверка, что порты свободны
docker compose up -d --build --wait          # сборка и запуск
docker compose exec -T web python manage.py loaddata docker/sqlite_dump.json   # данные, только первый раз
docker compose ps
```

Если репозиторий приватный, `git clone` попросит логин и **токен** GitHub (Settings → Developer settings → Personal access tokens), а не пароль.

---

## 3. Проверка

Открыть в браузере:
- `http://АДРЕС:WEB_PORT/nariad/` — CRM;
- `http://АДРЕС:WEB_PORT/` — JSON с версией приложения и данными из БД;
- `http://АДРЕС:WEB_PORT/dropbox/` — раздел Dropbox (ЛР4).

Или с сервера:

```bash
curl -s http://localhost:18080/ | head
```

Создать администратора для `/admin/`:

```bash
cd ~/crm && docker compose exec web python manage.py createsuperuser
```

---

## 4. Обновление после изменений в коде

**Способ А:** закоммитить изменения и повторить ту же команду (без `--load-data`):

```bash
./deploy/deploy.sh student05@192.168.10.5
```

**Способ Б:** на сервере:

```bash
cd ~/crm && git pull && docker compose up -d --build --wait
```

Данные БД при обновлении сохраняются: они лежат в томе `pgdata`, а не в контейнере.

---

## 5. Смена портов

- **Способ А:** поменять порт в `.env.server` (или передать `--port N` / `--db-port N`) и снова запустить `deploy.sh`.
- **Способ Б:** на сервере поменять `WEB_PORT` / `DB_PORT` в `~/crm/.env`, затем:

  ```bash
  ./deploy/ports.sh && docker compose up -d --wait
  ```

Все порты проекта:

| Переменная | Что это | По умолчанию |
|---|---|---|
| `WEB_PORT` | порт сайта на сервере | 8000 |
| `WEB_BIND` | интерфейс сайта (`127.0.0.1` — только локально, например за nginx) | 0.0.0.0 |
| `DB_PORT` | порт PostgreSQL на сервере | 5432 |
| `DB_BIND` | интерфейс БД (`127.0.0.1` — только с самого сервера) | 127.0.0.1 |
| `APP_PORT` | порт gunicorn внутри контейнера, менять не нужно | 8000 |
| `SWARM_HTTP_PORT`, `REGISTRY_PORT` | порты Swarm-фермы ЛР3 (см. п. 7) | 80, 5000 |
| `MONGO_PORT`, `MONGO_BIND` (`lab6_mongodb/.env`) | MongoDB ЛР6 (см. п. 7б) | 27017, 127.0.0.1 |
| `WP_PORT`, `WP_URL` (`lab7_wordpress/.env`) | сайт WordPress ЛР7 | 8081 |
| `PMA_PORT`, `PMA_BIND` (`lab7_wordpress/.env`) | phpMyAdmin ЛР7 | 8082, 127.0.0.1 |

Проверить порты любой лабы на машине: `./deploy/ports.sh` (CRM), `./deploy/ports.sh lab6_mongodb`, `./deploy/ports.sh lab7_wordpress`.

`DJANGO_ALLOWED_HOSTS` указывается **без порта**: порт можно менять, не трогая его.

---

## 6. Управление

Все команды — на сервере, в `~/crm`:

```bash
docker compose ps                     # состояние
docker compose logs -f web            # логи сайта (Ctrl+C — выход)
docker compose logs db                # логи БД
docker compose restart web            # перезапуск сайта
docker compose stop                   # остановить (данные сохраняются)
docker compose start                  # запустить снова
docker compose down                   # удалить контейнеры (том pgdata остаётся)
docker compose down -v                # удалить ВСЁ, включая базу

# резервная копия БД и восстановление
docker compose exec -T db pg_dump -U crm crm > backup.sql
docker compose exec -T db psql -U crm crm < backup.sql

# консоль БД
docker compose exec db psql -U crm crm
```

Контейнеры запущены с `restart: unless-stopped`: после перезагрузки сервера они поднимутся сами.

---

## 7. Swarm-ферма ЛР3 на сервере (если нужно показать там)

Нужны ещё 2 порта от преподавателя: для сайта фермы и для registry.

```bash
cd ~/crm
SWARM_HTTP_PORT=18081 REGISTRY_PORT=15000 ./swarm/cluster.sh up
./swarm/cluster.sh status
./swarm/cluster.sh down               # удалить ферму
```

Ферма запускает 4 контейнера `docker:dind` в режиме `--privileged`. На общем сервере это может быть запрещено, тогда показывайте ЛР3 на ноутбуке.

---

## 7б. ЛР6 (MongoDB) и ЛР7 (WordPress) на сервере

Тот же `deploy.sh` с опцией `--stack`. Настройки каждой лабы лежат в её каталоге: `<лаба>/.env.server` на компьютере копируется в `<лаба>/.env` на сервере.

**ЛР6 — нужен 1 порт** (MongoDB):

```bash
cp lab6_mongodb/.env.example lab6_mongodb/.env.server     # MONGO_PORT=выданный порт
./deploy/deploy.sh student05@192.168.10.5 --stack lab6_mongodb

# демонстрация на сервере
ssh student05@192.168.10.5
cd ~/crm/lab6_mongodb
docker compose exec mongo mongo /lab/shell_demo.js
docker compose run --rm script
```

`MONGO_BIND=127.0.0.1` (по умолчанию) — к базе можно подключиться только с самого сервера; `0.0.0.0` — откуда угодно (без пароля, только на время сдачи).

**ЛР7 — нужно 2 порта** (сайт и phpMyAdmin):

```bash
cp lab7_wordpress/.env.example lab7_wordpress/.env.server
```

В `lab7_wordpress/.env.server`:

```ini
WP_PORT=18081
WP_URL=http://192.168.10.5:18081      # адрес сайта = адрес сервера + WP_PORT
PMA_PORT=18082
PMA_BIND=0.0.0.0                      # чтобы открыть phpMyAdmin с компьютера (иначе только с сервера)
MAP_LL=долгота,широта                 # точка на Яндекс.Карте
```

Пароли (`MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `WP_ADMIN_PASSWORD`) можно оставить пустыми: сервер сгенерирует их при первом деплое, а при следующих деплоях они сохранятся.

```bash
./deploy/deploy.sh student05@192.168.10.5 --stack lab7_wordpress
ssh student05@192.168.10.5 "grep -E '^WP_ADMIN_(USER|PASSWORD)=' crm/lab7_wordpress/.env"   # вход в /wp-admin/
```

Скрипт установит WordPress, тему и плагины и наполнит сайт так же, как на ноутбуке.

Сменить порт или адрес сайта потом:

```bash
ssh student05@192.168.10.5
cd ~/crm/lab7_wordpress
sed -i 's/^WP_PORT=.*/WP_PORT=18085/' .env
./setup.sh url http://192.168.10.5:18085
```

Все три проекта (CRM, ЛР6, ЛР7) могут работать на одном сервере одновременно, каждый на своих портах.

---

## 8. Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `deploy.sh`: `ЗАНЯТ другим процессом` | порт уже кем-то занят. Попросите другой порт и поменяйте `WEB_PORT`/`DB_PORT` |
| `Permission denied (publickey)` | не настроен вход по ключу (п. 2А) или нужен `SSH_OPTS="-i путь_к_ключу"` |
| `permission denied ... docker.sock` | пользователь не в группе `docker`: `sudo usermod -aG docker $USER` и перезайти; без `sudo` — к преподавателю |
| В браузере `Bad Request (400)` | адрес сервера не прописан в `DJANGO_ALLOWED_HOSTS` → поправить `.env`, затем `docker compose up -d` |
| Сайт не открывается извне, а `curl localhost:ПОРТ` на сервере работает | порт закрыт файрволом сервера: `sudo ufw allow 18080/tcp` или к преподавателю |
| `web` не становится `healthy`, в логах `password authentication failed` | поменяли `POSTGRES_PASSWORD` после первого запуска. Вернуть старый пароль, или `docker compose down -v` (база удалится) и запустить заново с `--load-data` |
| `Waiting for database...` бесконечно | БД не стартовала: `docker compose logs db` |
| `CSRF verification failed` при отправке форм | сайт открыт через https или прокси: добавить адрес в `DJANGO_CSRF_TRUSTED_ORIGINS`, например `https://crm.example.com` |
| Нет стилей на страницах | смотреть `docker compose logs web`: при старте должен пройти `collectstatic` |
