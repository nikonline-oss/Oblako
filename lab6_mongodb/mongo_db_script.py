"""ЛР6: CRUD-операции с MongoDB из Python через PyMongo (часть 2 методички).

Запуск в Docker:   docker compose run --rm script
Запуск локально:   pip install -r requirements.txt && python mongo_db_script.py
Адрес сервера берётся из MONGO_URI (по умолчанию mongodb://localhost:27017).
"""
import os

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Create the client
client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))

# Connect to our database
db = client['SeriesDB']

# Fetch our series collection
series_collection = db['series']


def insert_document(collection, data):
    """ Function to insert a document into a collection and
    return the document's id.
    """
    return collection.insert_one(data).inserted_id


def find_document(collection, elements, multiple=False):
    """ Function to retrieve single or multiple documents from a provided
    Collection using a dictionary containing a document's elements.
    """
    if multiple:
        results = collection.find(elements)
        return [r for r in results]
    else:
        return collection.find_one(elements)


def update_document(collection, query_elements, new_values):
    """ Function to update a single document in a collection.
    """
    collection.update_one(query_elements, {'$set': new_values})


def delete_document(collection, query):
    """ Function to delete a single document from a collection.
    """
    collection.delete_one(query)


def step(title):
    print(f'\n=== {title}')


if __name__ == '__main__':
    print('MongoDB server version:', client.server_info()['version'])
    # Чтобы скрипт можно было запускать повторно, убираем записи от прошлого запуска
    series_collection.delete_many({'name': {'$in': ['FRIENDS', 'F.R.I.E.N.D.S']}})
    series_collection.delete_one({'_id': '1'})

    step('Создание документа')
    new_show = {
        "name": "FRIENDS",
        "year": 1994
    }
    print(insert_document(series_collection, new_show))

    step('Документ со своим _id и повторная вставка того же _id')
    print(insert_document(series_collection, {"_id": "1", "name": "FRIENDS", "year": 1994}))
    try:
        insert_document(series_collection, {"_id": "1", "name": "FRIENDS", "year": 1994})
    except DuplicateKeyError as e:
        print('DuplicateKeyError:', e.details['errmsg'])

    step('Получение одного документа')
    result = find_document(series_collection, {'name': 'FRIENDS'})
    print(result)

    step('Получение нескольких документов (multiple=True)')
    for doc in find_document(series_collection, {'name': 'FRIENDS'}, multiple=True):
        print(doc)

    step('Обновление документа')
    new_show = {
        "name": "FRIENDS",
        "year": 1995
    }
    id_ = insert_document(series_collection, new_show)
    update_document(series_collection, {'_id': id_}, {'name': 'F.R.I.E.N.D.S'})
    result = find_document(series_collection, {'_id': id_})
    print(result)

    step('Удаление документа')
    delete_document(series_collection, {'_id': id_})
    result = find_document(series_collection, {'_id': id_})
    print(result)

    step('Все документы коллекции series')
    for doc in find_document(series_collection, {}, multiple=True):
        print(doc)
