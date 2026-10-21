# Лабораторная работа №6 «Практическая работа с NoSQL базой данных MongoDB»

**Цель:** развернуть NoSQL-решение MongoDB на Ubuntu 20.04, научиться работать с ним через Mongo Shell и из Python с помощью PyMongo.

**Реализация:** каталог [lab6_mongodb/](lab6_mongodb/). MongoDB 4.4 ставится **по шагам методички** в контейнере Ubuntu 20.04 ([ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile)). Так установку можно повторить на любом компьютере с Docker, в том числе на Windows и на сервере.

| Файл | Что это |
|---|---|
| [ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile) | шаг 1: ключ GPG, репозиторий `focal/mongodb-org/4.4`, `apt install mongodb-org` |
| [docker-compose.yml](lab6_mongodb/docker-compose.yml) | сервер `mongo` (порт и том с данными) + сервис `script` для Python-скрипта |
| [shell_demo.js](lab6_mongodb/shell_demo.js) | CRUD в Mongo Shell над `SeriesDB.series` (команды из методички) |
| [mongo_db_script.py](lab6_mongodb/mongo_db_script.py) | скрипт PyMongo: `insert_document`, `find_document`, `update_document`, `delete_document` |
| [Dockerfile](lab6_mongodb/Dockerfile), [requirements.txt](lab6_mongodb/requirements.txt) | образ Python 3.12 с `pymongo==4.10.1` для запуска скрипта |

## Запуск

```bash
cd lab6_mongodb
docker compose up -d --build --wait                     # шаги 1–2: установка и запуск MongoDB
docker compose exec mongo mongo --eval 'db.runCommand({ connectionStatus: 1 })'
docker compose exec mongo mongo /lab/shell_demo.js      # Mongo Shell
docker compose run --rm script                          # PyMongo
docker compose exec mongo mongo                         # интерактивная оболочка
```

Порт задаётся в `lab6_mongodb/.env` (по умолчанию `MONGO_PORT=27017`, `MONGO_BIND=127.0.0.1`), см. [.env.example](lab6_mongodb/.env.example).

## Часть 1. Установка MongoDB в Ubuntu 20.04

### Шаг 1 — установка

Команды методички в [ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile):

```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" \
  > /etc/apt/sources.list.d/mongodb-org-4.4.list
apt-get update
apt-get install -y mongodb-org
```

Результат сборки:

```
Setting up mongodb-org-shell (4.4.31) ...
Setting up mongodb-org-server (4.4.31) ...
Setting up mongodb-org (4.4.31) ...
/var/lib/dpkg/info/mongodb-org-server.postinst: 44: systemctl: not found
```

Сообщение `systemctl: not found` ожидаемо: в контейнере нет systemd, поэтому установщик не может зарегистрировать службу. На обычной Ubuntu его не будет.

### Шаг 2 — запуск и проверка

Вместо `sudo systemctl start mongod` сервер запускается как процесс контейнера: `mongod --bind_ip_all --dbpath /data/db`.

```
$ docker compose exec mongo mongo --eval 'db.runCommand({ connectionStatus: 1 })'
MongoDB shell version v4.4.31
connecting to: mongodb://127.0.0.1:27017/?compressors=disabled&gssapiServiceName=mongodb
MongoDB server version: 4.4.31
{
	"authInfo" : {
		"authenticatedUsers" : [ ],
		"authenticatedUserRoles" : [ ]
	},
	"ok" : 1
}
```

`"ok" : 1` — сервер работает, порт 27017.

### Шаг 3 — управление службой

| systemd (методичка) | Docker Compose |
|---|---|
| `sudo systemctl start mongod` | `docker compose start mongo` |
| `sudo systemctl stop mongod` | `docker compose stop mongo` |
| `sudo systemctl restart mongod` | `docker compose restart mongo` |
| `sudo systemctl status mongod` | `docker compose ps` (статус `healthy`), `docker compose logs mongo` |
| `sudo systemctl enable mongod` | `restart: unless-stopped` в compose — запуск вместе с Docker |
| `sudo systemctl disable mongod` | `docker update --restart=no lab6_mongodb-mongo-1` |

Все команды проверены: после `stop`/`start`/`restart` контейнер снова становится `healthy`. Данные хранятся в томе `mongodata` и переживают перезапуск.

На «живой» Ubuntu 20.04 (если она есть) выполняются ровно те же команды из шага 1 с `sudo`, а затем `sudo systemctl start mongod` и `sudo systemctl enable mongod`.

## Часть 2. Работа с MongoDB

### Mongo Shell

[shell_demo.js](lab6_mongodb/shell_demo.js): `use SeriesDB` → `insertOne` / `insertMany` → `find({})` → `find({ year: 2013 })` → `updateOne` → `deleteMany`. Вывод (сокращён):

```
> db.series.insertMany([...])
{ "acknowledged" : true, "insertedIds" : [ ObjectId("..."), ObjectId("..."), ObjectId("...") ] }

> db.series.find({ year: 2013 })  -- SELECT * FROM series WHERE year = 2013
[ { "name" : "The Blacklist", "year" : 2013 }, { "name" : "House of Cards", "year" : 2013 } ]

> db.series.updateOne({ name: "Suits" }, { $set: { year: 2010 } })
{ "acknowledged" : true, "matchedCount" : 1, "modifiedCount" : 1 }

> db.series.deleteMany({ year: 2012 })
{ "acknowledged" : true, "deletedCount" : 1 }

> db.series.find({})  -- после удаления
[ The Blacklist 2013, House of Cards 2013, Suits 2010 ]
```

### PyMongo

[mongo_db_script.py](lab6_mongodb/mongo_db_script.py) — функции из методички. Код исправлен: в методичке `import pymongo`, а затем используется `MongoClient` без префикса. Адрес сервера берётся из `MONGO_URI`.

```
$ docker compose run --rm script
MongoDB server version: 4.4.31

=== Создание документа
6ad924541ca40c87470efe60

=== Документ со своим _id и повторная вставка того же _id
1
DuplicateKeyError: E11000 duplicate key error collection: SeriesDB.series index: _id_ dup key: { _id: "1" }

=== Получение одного документа
{'_id': ObjectId('6ad924541ca40c87470efe60'), 'name': 'FRIENDS', 'year': 1994}

=== Получение нескольких документов (multiple=True)
{'_id': ObjectId('6ad924541ca40c87470efe60'), 'name': 'FRIENDS', 'year': 1994}
{'_id': '1', 'name': 'FRIENDS', 'year': 1994}

=== Обновление документа
{'_id': ObjectId('6ad924541ca40c87470efe61'), 'name': 'F.R.I.E.N.D.S', 'year': 1995}

=== Удаление документа
None
```

Скрипт можно запускать повторно: в начале он удаляет записи, оставшиеся от прошлого запуска.

## Развёртывание на сервере

```bash
cp lab6_mongodb/.env.example lab6_mongodb/.env.server   # вписать выданный порт: MONGO_PORT=...
./deploy/deploy.sh user@server --stack lab6_mongodb
```

Проверено на тестовом сервере с `MONGO_PORT=27018`: `deploy.sh` проверил порт, собрал образ, контейнер стал `healthy`. `shell_demo.js` и `mongo_db_script.py` на сервере выполнились. Подробнее — [DEPLOY.md](DEPLOY.md).

## Выводы

MongoDB хранит JSON-подобные документы (BSON) в коллекциях без заранее заданной схемы. Документы одной коллекции могут иметь разный набор полей, `_id` создаётся автоматически и уникален (повторная вставка даёт `DuplicateKeyError`). Запросы — это документы-фильтры (`{ year: 2013 }` вместо `WHERE year = 2013`), изменения — операторы вида `$set`. PyMongo повторяет API оболочки (`insert_one`, `find`, `find_one`, `update_one`, `delete_one`), документы в Python — обычные словари.
