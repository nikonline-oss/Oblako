# Лабораторная работа №6 «Практическая работа с NoSQL базой данных MongoDB»

**Цель:** развернуть NoSQL-решение MongoDB на Ubuntu 20.04, научиться работать с ним через Mongo Shell и из Python с помощью PyMongo.

**Реализация:** каталог [lab6_mongodb/](lab6_mongodb/). MongoDB 4.4 ставится **по шагам методички** в контейнере Ubuntu 20.04 ([ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile)). Так установку можно повторить на любом компьютере с Docker, в том числе на Windows и на сервере.

| Файл | Что это |
|---|---|
| [ubuntu/Dockerfile](lab6_mongodb/ubuntu/Dockerfile) | шаг 1: ключ GPG, репозиторий `focal/mongodb-org/4.4`, `apt install mongodb-org` |
| сервис `mongo` в общем [docker-compose.yml](docker-compose.yml) | сервер MongoDB из этого образа, том `mongodata`; он же хранит данные CRM (журнал, сериалы) |
| [shell_demo.js](lab6_mongodb/shell_demo.js) | CRUD в Mongo Shell над `SeriesDB.series` (команды из методички) |
| [mongo_db_script.py](lab6_mongodb/mongo_db_script.py) | скрипт PyMongo: `insert_document`, `find_document`, `update_document`, `delete_document` |
| [Dockerfile](lab6_mongodb/Dockerfile), [requirements.txt](lab6_mongodb/requirements.txt) | образ Python 3.12 с `pymongo==4.10.1` для запуска скрипта (сервис `lab6-script`) |
| [activity_log/](activity_log/) | MongoDB в CRM: CRUD сериалов, журнал действий, статистика (часть 3) |

## Запуск

MongoDB запускается вместе со всем проектом:

```bash
./project.sh up                                         # шаги 1–2: сборка образа по методичке и запуск
./project.sh lab6                                       # connectionStatus + Mongo Shell + PyMongo подряд
docker compose exec mongo mongo SeriesDB                # интерактивная оболочка
```

По отдельности:

```bash
docker compose exec mongo mongo --eval 'db.runCommand({ connectionStatus: 1 })'
docker compose exec mongo mongo /lab/shell_demo.js      # Mongo Shell
docker compose run --rm lab6-script                     # PyMongo
```

Наружу MongoDB порт не публикует. Для подключения извне (например, MongoDB Compass) в `.env` задаётся `COMPOSE_PROFILES=db-ports`, порт — `MONGO_PORT` (по умолчанию 27017, только `127.0.0.1`).

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

## Часть 3. MongoDB в CRM

PyMongo используется не только в учебном скрипте, но и в самой CRM: пункт **MongoDB** в верхнем меню. Там три вкладки: «Сериалы (CRUD)», «Журнал», «Статистика».

### 3.1. Сериалы: создание, просмотр, редактирование, удаление

Адрес `/journal/series/`. Это веб-интерфейс к той же коллекции `SeriesDB.series`, с которой работают Mongo Shell и скрипт из части 2: сериалы, добавленные скриптом, видны в CRM, и наоборот. Код — [activity_log/series.py](activity_log/series.py), функции названы как в методичке (`insert_document`, `find_document`, `update_document`, `delete_document`).

| Действие | Что делает интерфейс | Операция MongoDB |
|---|---|---|
| Просмотр | таблица с поиском по названию, фильтром по жанру и годам, сортировкой; запрос показан на странице | `find({"name": {"$regex": …, "$options": "i"}, "genres": "драма", "year": {"$gte": …}}).sort(…)` |
| Создание | форма «Добавить» | `insert_one(...)`, в сообщении — новый `_id` |
| Редактирование | форма с текущими значениями и исходным документом | `update_one({_id}, {"$set": …, "$unset": …})` |
| Удаление | кнопка 🗑 с подтверждением | `delete_one({_id})` |

**Гибкая схема — главное отличие от SQL:**
- обязательны только `name` и `year`;
- пустые поля в документ не записываются;
- жанры хранятся **массивом** (`["драма", "комедия"]`), и фильтр «жанр = драма» находит документ, если в массиве есть такой элемент;
- «Дополнительные поля» в форме («страна: США», «серий: 236», «завершён: да») становятся полями документа с нужными типами (строка, число, логическое значение). У каждого сериала свой набор полей, и менять схему коллекции для этого не надо;
- если при редактировании поле убрать, оно удаляется из документа через `$unset`.

Пример документа после создания через форму:

```
{
  "_id": ObjectId("…"),
  "name": "Friends", "year": 1994,
  "genres": ["комедия", "ситком"],
  "seasons": 10, "rating": 8.9,
  "страна": "США", "серий": 236, "завершён": true
}
```

Создание, изменение и удаление сериалов тоже пишутся в журнал (раздел «Сериал (MongoDB)»), с «было → стало».

### 3.2. Журнал действий

Приложение [activity_log/](activity_log/) записывает в MongoDB каждое создание, изменение и удаление записей CRM: наряды, сотрудники, товары, организации, доверенности и т.д. Вкладка **«Журнал»**, адрес `/journal/`.

**Почему здесь подходит именно NoSQL.** У событий нет общей схемы: у наряда 8 полей, у единицы измерения одно, у изменения вместо данных — пары «было → стало». В PostgreSQL для этого понадобилась бы таблица с JSON-полем или по таблице на каждую модель. В MongoDB это просто документы в одной коллекции `activity`:

```
{
  "timestamp" : ISODate("2026-10-21T22:01:47.089Z"),
  "action" : "update",
  "model" : "units.Unit",
  "model_verbose" : "Единица измерения",
  "object_id" : 3,
  "object_repr" : "Тестовая единица (изм.)",
  "changes" : { "name" : { "old" : "Тестовая единица", "new" : "Тестовая единица (изм.)" } },
  "user" : null, "ip" : "172.20.0.1", "path" : "/units/edit/3/"
}
```

Внешние ключи сохраняются вложенными документами `{id, repr}`, например `"unit": {"id": 1, "repr": "шт"}`. Поэтому в журнале видно название связанного объекта, даже если тот уже удалён.

| Что | Как сделано |
|---|---|
| Запись событий | Django-сигналы `pre_save` / `post_save` / `post_delete` → `collection.insert_one(...)` ([signals.py](activity_log/signals.py), [mongo.py](activity_log/mongo.py)) |
| Пользователь и IP | middleware запоминает текущий запрос |
| Изменения без лишнего шума | сохранение без изменений не пишется, загрузка фикстур (`loaddata`) — тоже |
| Индексы | `by_time` (`timestamp: -1`), `by_object` (`model, object_id, timestamp`), полнотекстовый `text_search` с `default_language: "russian"` |
| Страница «Журнал» | `find(query).sort({timestamp: -1}).skip().limit(50)`, фильтры по разделу, действию, ID объекта и датам; поиск через `$text` («тонны» находит «тонна»); сам запрос к MongoDB показывается на странице |
| Карточка события | `find_one({_id: ObjectId(...)})`: таблица «было → стало» и исходный BSON-документ |
| Статистика | 4 конвейера `aggregate()`: `$group` по разделам и действиям, `$dateToString` по дням, топ-10 объектов. Плюс `collStats` и список индексов, а сами pipeline показаны на странице |
| Надёжность | таймаут подключения 2 с; если MongoDB недоступна, CRM сохраняет записи как обычно, в лог пишется предупреждение, а страница журнала объясняет, что случилось |

CRM использует ту же MongoDB, что собрана по методичке (сервис `mongo` в общем [docker-compose.yml](docker-compose.yml), том `mongodata`): журнал — в БД `crm`, сериалы — в `SeriesDB`. Наружу порт **не публикуется**, к нему ходит только `web` по внутренней сети, так что лишний порт на сервере не нужен. Консоль:

```bash
docker compose exec mongo mongo crm --eval 'db.activity.find().sort({timestamp: -1}).limit(3).forEach(printjson)'
```

На Render своей MongoDB нет: журнал там выключен, пока не задан `MONGO_URI`. Можно взять бесплатный кластер MongoDB Atlas (M0) и вписать его строку подключения в переменную `MONGO_URI` в Dashboard.

### 3.3. Проверка

- **13 автотестов** ([activity_log/tests.py](activity_log/tests.py)) на настоящей MongoDB в отдельных тестовых БД:
  - журнал: создание, изменение и удаление, внешние ключи, Decimal и даты, пользователь и IP, фильтры, полнотекстовый поиск, карточка события, агрегации, работа CRM без MongoDB и при её падении;
  - сериалы: создание гибкого документа (массив жанров, доп. поля с типами, пустые поля не сохраняются), поиск, фильтр по жанру и годам, сортировка, редактирование с `$set`/`$unset`, удаление только через POST, проверка формы.
- **Вживую через интерфейс CRM:**
  - сериал «Тестовый сериал» создан с жанрами и доп. полями «страна: Россия», «серий: 16»;
  - отредактирован: новое название, удалены поле «серий» и число сезонов;
  - найден поиском «тестовый» без учёта регистра;
  - удалён;
  - в журнале — 3 события с одним `_id`.
- **Журнал при изменении записей CRM:** единица измерения создана, изменена и удалена — в журнале 3 события с IP, карточка показывает «Название: Тестовая единица → Тестовая единица (изм.)», в `mongo` shell те же документы.

## Развёртывание на сервере

MongoDB входит в общий проект и выкладывается вместе с ним (`./deploy/deploy.sh user@server`, см. [DEPLOY.md](DEPLOY.md)). Отдельный порт для неё не нужен. Демонстрация на сервере: `./project.sh lab6` и раздел «MongoDB» в CRM.

## Выводы

MongoDB хранит JSON-подобные документы (BSON) в коллекциях без заранее заданной схемы. Документы одной коллекции могут иметь разный набор полей, `_id` создаётся автоматически и уникален (повторная вставка даёт `DuplicateKeyError`). Запросы — это документы-фильтры (`{ year: 2013 }` вместо `WHERE year = 2013`), изменения — операторы вида `$set`. PyMongo повторяет API оболочки (`insert_one`, `find`, `find_one`, `update_one`, `delete_one`), документы в Python — обычные словари.
