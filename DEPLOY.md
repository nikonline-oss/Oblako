# Развёртывание проекта на удалённом сервере

Весь проект (все лабы) запускается одной командой `./project.sh up` из одного [docker-compose.yml](docker-compose.yml) с одним файлом настроек `.env`:

```
                ┌── WEB_PORT ──▶ web (CRM: Django + gunicorn) ──┬──▶ db    (PostgreSQL 17)
браузер ────────┤                                               └──▶ mongo (MongoDB 4.4, ЛР6)
                ├── WP_PORT ───▶ wordpress ──┐
                └── PMA_PORT ──▶ phpmyadmin ─┴──────────────────────▶ wp-db (MySQL 8.4)
```

Наружу открыты только **3 порта**. PostgreSQL, MongoDB и MySQL работают во внутренних сетях Docker и порты сервера не занимают. При необходимости их можно открыть (п. 5).

Что делать — ниже. Как показывать каждую лабу — в [LABS.md](LABS.md).

---

## 0. Что узнать у преподавателя

| Что | Пример | Куда пойдёт |
|---|---|---|
| Адрес сервера | `192.168.10.5` | `user@адрес` в командах, `PUBLIC_HOST` |
| Логин SSH (и пароль или ключ) | `student05` | `user@адрес` |
| Порт SSH, если не 22 | `2222` | `SSH_PORT` |
| **3 порта**: CRM, WordPress, phpMyAdmin | `18080`, `18081`, `18082` | `WEB_PORT`, `WP_PORT`, `PMA_PORT` |
| Можно ли `docker` без `sudo` | `docker ps` работает | — |

Ещё 2 порта нужны, только если на сервере показывать Swarm-ферму ЛР3 (п. 7). Тогда понадобятся ещё права на `--privileged`-контейнеры.

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

На своём компьютере, в папке проекта:

```bash
cp .env.example .env.server
```

В `.env.server` достаточно поменять:

```ini
PUBLIC_HOST=192.168.10.5     # адрес сервера (как его открывают в браузере)
WEB_PORT=18080               # выданные порты
WP_PORT=18081
PMA_PORT=18082
PMA_BIND=0.0.0.0             # чтобы phpMyAdmin открывался с компьютера (иначе только с сервера)

DROPBOX_APP_KEY=...          # ЛР4, можно оставить пустым
MAP_LL=долгота,широта        # точка на карте WordPress (ЛР7)
```

Пароли и ключи (`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`, `MYSQL_*`, `WP_ADMIN_PASSWORD`) оставьте **пустыми**. Сервер сгенерирует их при первом запуске и запишет в свой `.env`, а при следующих деплоях они сохранятся.

`.env.server` не попадает в git.

---

## 2А. Выкладка одной командой (с компьютера)

Нужны Git Bash (на Windows) и доступ к серверу по SSH.

**Один раз — вход по ключу:**

```bash
ssh-keygen -t ed25519                          # если ключа ещё нет (Enter на все вопросы)
ssh-copy-id -p 22 student05@192.168.10.5
```

**Деплой** (из папки проекта):

```bash
./deploy/deploy.sh student05@192.168.10.5
```

- SSH не на 22 порту: `SSH_PORT=2222 ./deploy/deploy.sh ...`
- другой ключ: `SSH_OPTS="-i ~/.ssh/my_key" ./deploy/deploy.sh ...`
- другой каталог на сервере (по умолчанию `~/crm`): `--dir labs/crm`
- вместе со Swarm-фермой ЛР3: `--swarm`

Что делает скрипт:
1. проверяет, что на сервере есть `docker compose`;
2. копирует файлы проекта в `~/crm` (без `.git`, `.env` и мусора);
3. переносит `.env.server` → `~/crm/.env`. Пустые значения берутся из уже существующего `.env` сервера, так что сгенерированные пароли не теряются;
4. если `PUBLIC_HOST` не задан, подставляет адрес из `user@адрес`;
5. запускает на сервере `./project.sh up`:
   - проверяет, свободны ли порты, и при конфликте останавливается и пишет, какой порт занят;
   - собирает и запускает контейнеры и ждёт, пока они станут `healthy`;
   - при первом запуске загружает данные CRM и устанавливает и наполняет WordPress;
   - печатает адреса всех лаб.

Конец вывода:

```
  ЛР2  CRM в Docker            http://192.168.10.5:18080/nariad/
  ЛР4  Dropbox                 http://192.168.10.5:18080/dropbox/
  ЛР5  версия/релиз (JSON)     http://192.168.10.5:18080/
  ЛР6  журнал CRM в MongoDB    http://192.168.10.5:18080/journal/      демо: ./project.sh lab6
  ЛР7  WordPress               http://192.168.10.5:18081/
       Консоль WordPress       http://192.168.10.5:18081/wp-admin/
       phpMyAdmin              http://192.168.10.5:18082/
```

Логин и пароль WordPress:

```bash
ssh student05@192.168.10.5 "grep -E '^(WP_ADMIN|MYSQL)_(USER|PASSWORD)=' crm/.env"
```

---

## 2Б. Выкладка вручную (на сервере)

Если SSH-скрипт с компьютера не работает, всё можно сделать на самом сервере.

```bash
ssh -p 22 student05@192.168.10.5

git clone -b init https://github.com/nikonline-oss/Oblako.git crm
cd crm
cp .env.example .env
nano .env                  # PUBLIC_HOST и порты, как в п. 1
./project.sh up
```

---

## 3. Проверка

```bash
./project.sh status                  # на сервере: контейнеры + адреса
./deploy/ports.sh                    # какие порты заняты проектом
```

Открыть в браузере адреса из вывода. Подробный сценарий показа каждой лабы — в [LABS.md](LABS.md).

Администратор CRM для `/admin/`:

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 4. Обновление после изменений в коде

С компьютера (закоммитить изменения не обязательно — копируются файлы как есть):

```bash
./deploy/deploy.sh student05@192.168.10.5
```

Или на сервере, если ставили через `git clone`:

```bash
cd ~/crm && git pull && ./project.sh up
```

Данные всех баз хранятся в томах Docker (`crm_pgdata`, `crm_mongodata`, `crm_wp-dbdata`, `crm_wpdata`) и при обновлении сохраняются. Повторно CRM и WordPress не наполняются.

---

## 5. Порты

Все — в `.env`:

| Переменная | Что | По умолчанию |
|---|---|---|
| `PUBLIC_HOST` | адрес, по которому открывают сайты | localhost |
| `WEB_PORT` / `WEB_BIND` | CRM | 8000 / 0.0.0.0 |
| `WP_PORT` / `WP_BIND` | WordPress | 8081 / 0.0.0.0 |
| `PMA_PORT` / `PMA_BIND` | phpMyAdmin (`127.0.0.1` — только с самого сервера) | 8082 / 127.0.0.1 |
| `COMPOSE_PROFILES=db-ports` | открыть PostgreSQL и MongoDB снаружи (pgAdmin, Compass) | выключено |
| `DB_PORT` / `DB_BIND` | PostgreSQL при `db-ports` | 5432 / 127.0.0.1 |
| `MONGO_PORT` / `MONGO_BIND` | MongoDB при `db-ports` | 27017 / 127.0.0.1 |
| `SWARM_HTTP_PORT`, `REGISTRY_PORT` | Swarm-ферма ЛР3 | 80, 5000 |
| `APP_PORT` | gunicorn внутри контейнера, менять не нужно | 8000 |

**Сменить порт:** поменять его в `.env.server` и повторить `./deploy/deploy.sh ...`, либо на сервере поменять в `.env` и выполнить `./project.sh up`. Если поменялся `WP_PORT` или `PUBLIC_HOST`, `project.sh` сам перепишет адреса внутри WordPress.

`DJANGO_ALLOWED_HOSTS` трогать не нужно: `PUBLIC_HOST` разрешается автоматически.

---

## 6. Управление

На сервере, в `~/crm`:

```bash
./project.sh status                 # состояние + адреса
./project.sh logs web               # логи (web, db, mongo, wordpress, wp-db, phpmyadmin), Ctrl+C — выход
./project.sh down                   # остановить всё (данные сохраняются)
./project.sh up                     # запустить снова
./project.sh lab6                   # демонстрация ЛР6 в консоли
./project.sh wp-reset               # собрать сайт WordPress заново (его БД удаляется)

# резервные копии
docker compose exec -T db pg_dump -U crm crm > crm.sql
docker compose exec -T mongo mongodump --archive > mongo.archive
docker compose exec -T wp-db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" wptest' > wordpress.sql
```

Контейнеры запущены с `restart: unless-stopped`: после перезагрузки сервера они поднимутся сами.

Удалить всё вместе с данными: `docker compose down -v`.

---

## 7. Swarm-ферма ЛР3 на сервере

Нужны ещё 2 порта (`SWARM_HTTP_PORT` — сайт фермы, `REGISTRY_PORT` — локальный registry, открыт только на 127.0.0.1) и разрешение запускать `--privileged`-контейнеры.

```bash
./deploy/deploy.sh student05@192.168.10.5 --swarm
# или на сервере:
./project.sh swarm up
./project.sh swarm status
./project.sh swarm down
```

Если на общем сервере `--privileged` запрещён, показывайте ЛР3 на ноутбуке.

---

## 8. Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `ЗАНЯТ другим процессом` | порт уже кем-то занят: попросите другой и поменяйте его в `.env.server` / `.env` |
| `Permission denied (publickey)` | не настроен вход по ключу (п. 2А) или нужен `SSH_OPTS="-i путь_к_ключу"` |
| `permission denied ... docker.sock` | пользователь не в группе `docker`: `sudo usermod -aG docker $USER` и перезайти; без `sudo` — к преподавателю |
| CRM: `Bad Request (400)` | сайт открыт не по `PUBLIC_HOST`: впишите правильный адрес в `.env` и выполните `./project.sh up` |
| Сайт не открывается извне, а `curl localhost:ПОРТ` на сервере работает | порт закрыт файрволом сервера: `sudo ufw allow 18080/tcp` или к преподавателю |
| WordPress: ссылки и картинки ведут на старый адрес | поменялся адрес: проверьте `PUBLIC_HOST`/`WP_PORT` в `.env` и выполните `./project.sh up` — он перепишет адреса |
| `web` не `healthy`, в логах `password authentication failed` | поменяли `POSTGRES_PASSWORD` после первого запуска. Верните старый пароль, или `docker compose down -v` (базы удалятся) и `./project.sh up` |
| Ошибка при скачивании плагинов WordPress | сеть оборвалась: просто повторите `./project.sh up`, он продолжит с того же места |
| `CSRF verification failed` | сайт открыт через https или прокси: добавьте адрес в `DJANGO_CSRF_TRUSTED_ORIGINS`, например `https://crm.example.com` |
