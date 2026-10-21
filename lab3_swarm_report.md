# Лабораторная работа №3 «Основы контейнерной виртуализации»

**Цель:** научиться работать с Docker-контейнерами и строить устойчивые приложения на базе Docker Swarm.

**Задание:** реализовать python-приложение с БД в виде swarm-фермы: один узел — «узел БД», остальные — «веб-серверные узлы», минимум 3 реплики веб-сервера, приложение отвечает на 80 порту, выполняет запрос к БД и устойчиво к падению реплики.

**Реализация:** Python-приложение — Django-проект **crm** (gunicorn), БД — **PostgreSQL 17**. Ферма запущена на ноутбуке: 4 узла Swarm, каждый — отдельный Docker Engine (docker-in-docker).

## Архитектура

```
                 host :80
                    │
     ┌──────────────▼──────────────────────────────────────────────┐
     │  Swarm ingress (routing mesh, балансировка запросов)         │
     └──────┬───────────────────┬───────────────────┬──────────────┘
   ┌────────▼───────┐  ┌────────▼───────┐  ┌────────▼───────┐  ┌────────────────┐
   │ worker1        │  │ worker2        │  │ worker3        │  │ manager        │
   │ role=web       │  │ role=web       │  │ role=web       │  │ role=db        │
   │ crm_web (реп.) │  │ crm_web (реп.) │  │ crm_web (реп.) │  │ crm_db         │
   └────────┬───────┘  └────────┬───────┘  └────────┬───────┘  │ postgres + том │
            └────────── overlay-сеть crm_backend ───┴──────────▶└────────────────┘
```

- `db`: 1 реплика, `placement: node.labels.role == db`, поэтому запускается только на `manager`.
- `web`: 3 реплики, `placement: node.labels.role == web`, не больше 2 на узел; порт `80:8000`, healthcheck, `restart_policy: any`.
- `migrate`: одноразовая задача, применяет миграции и загружает данные из старой SQLite (`docker/sqlite_dump.json`).
- Образ приложения хранится в registry (локальный `registry:2` вместо DockerHub), узлы скачивают его оттуда.

## Файлы

| Файл | Назначение |
|---|---|
| [swarm/docker-stack.yml](swarm/docker-stack.yml) | описание стека Swarm (db, migrate, web) |
| [swarm/cluster.sh](swarm/cluster.sh) | создание/удаление локальной фермы из 4 узлов и деплой стека |
| [crm/views.py](crm/views.py) | `GET /`: JSON с именем контейнера-реплики и результатами запросов к БД |
| [docker/entrypoint.sh](docker/entrypoint.sh) | `RUN_MIGRATIONS=0` отключает миграции в репликах web |

## Ход работы

```bash
# Поднять ферму и развернуть стек (Git Bash)
./swarm/cluster.sh up
```

Что делает скрипт (основные команды):

```bash
docker network create swarm-lab
docker run -d --name registry --network swarm-lab -p 5000:5000 registry:2
docker run -d --privileged --name manager --hostname manager --network swarm-lab -p 80:80 docker:27-dind --insecure-registry registry:5000
docker run -d --privileged --name worker1 ... (аналогично worker2, worker3)

docker exec manager docker swarm init --advertise-addr eth0
docker exec manager docker swarm join-token -q worker
docker exec worker1 docker swarm join --token <TOKEN> manager:2377      # и worker2, worker3

docker exec manager docker node update --label-add role=db  manager
docker exec manager docker node update --label-add role=web worker1    # и worker2, worker3

docker build -t localhost:5000/crm-web:latest .
docker push localhost:5000/crm-web:latest
docker exec manager docker stack deploy -c /docker-stack.yml crm
```

### 1. Узлы фермы

```
$ docker exec manager docker node ls
HOSTNAME   STATUS    AVAILABILITY   MANAGER STATUS   ENGINE VERSION
manager    Ready     Active         Leader           27.5.1
worker1    Ready     Active                          27.5.1
worker2    Ready     Active                          27.5.1
worker3    Ready     Active                          27.5.1
```

### 2. БД только на «узле БД», 3 реплики web на веб-узлах

```
$ docker exec manager docker stack services crm
NAME          MODE         REPLICAS               IMAGE                          PORTS
crm_db        replicated   1/1                    postgres:17-alpine
crm_migrate   replicated   0/1                    registry:5000/crm-web:latest
crm_web       replicated   3/3 (max 2 per node)   registry:5000/crm-web:latest   *:80->8000/tcp

$ docker exec manager docker service ps crm_db crm_web
NAME        NODE      CURRENT STATE
crm_db.1    manager   Running
crm_web.1   worker2   Running
crm_web.2   worker3   Running
crm_web.3   worker1   Running
```

(`crm_migrate` — 0/1, потому что задача выполнилась и завершилась: `Complete`.)

### 3. Приложение отвечает на 80 порту и выполняет запросы к БД

```
$ curl http://localhost/
{
  "web_container": "a8ff4e3ec0cf",
  "db_host": "db",
  "db_ip": "10.0.1.10",
  "db_version": "PostgreSQL 17.11 on x86_64-pc-linux-musl",
  "db_time": "2026-10-21T18:19:32.057609+00:00",
  "nariad_count": 2,
  "employee_count": 2
}
```

Балансировка: 9 запросов подряд распределились поровну между 3 репликами:

```
      3 "web_container": "3ad5ddb1dc25"
      3 "web_container": "483227ce761a"
      3 "web_container": "a8ff4e3ec0cf"
```

Полный интерфейс CRM тоже работает: http://localhost/nariad/ → 200.

### 4. Устойчивость к падению реплики

Во время непрерывных запросов (60 шт., раз в 0,5 с) контейнер реплики на `worker2` был убит:

```bash
docker exec worker2 sh -c 'docker rm -f $(docker ps -q --filter name=crm_web)'
```

Результат: **60 из 60 запросов успешны (200)**. Swarm заметил падение и сам запустил новую реплику:

```
crm_web.1 worker2 Running   Running 22 seconds ago
crm_web.1 worker2 Shutdown  Failed 33 seconds ago
```

### 5. Устойчивость к падению целого веб-узла

```bash
docker stop worker3
```

Результат: **80 из 80 запросов успешны**. Узел `worker3` перешёл в `Down`, его реплика переехала на `worker1`:

```
crm_web.1 worker2 Running
crm_web.2 worker1 Running 20 seconds ago
crm_web.3 worker1 Running
```

После `docker start worker3` узел вернулся в состояние `Ready`.

## Публикация образа на DockerHub (по подсказке из задания)

```bash
docker login
docker build -t <dockerhub_login>/crm-web:latest .
docker push <dockerhub_login>/crm-web:latest
# деплой стека с образом из DockerHub (например, на play-with-docker.com):
WEB_IMAGE=<dockerhub_login>/crm-web:latest docker stack deploy -c docker-stack.yml crm
```

На play-with-docker: создать 4 инстанса, на первом выполнить `docker swarm init --advertise-addr eth0`, на остальных — `docker swarm join ...`, проставить метки `role=db`/`role=web` командой `docker node update --label-add`, загрузить `docker-stack.yml` и выполнить команду деплоя выше.

## Полезные команды

```bash
./swarm/cluster.sh status                                 # узлы, сервисы, реплики
docker exec manager docker service scale crm_web=5        # масштабирование
docker exec manager docker service logs crm_web           # логи всех реплик
./swarm/cluster.sh down                                   # удалить ферму
```
