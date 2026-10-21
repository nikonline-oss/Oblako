"""CRUD над коллекцией SeriesDB.series — те же функции, что в скрипте ЛР6
(lab6_mongodb/mongo_db_script.py), только для веб-интерфейса CRM."""
import re

from bson import ObjectId
from django.conf import settings
from pymongo import ASCENDING, DESCENDING

from .mongo import _client, log_document_event

MODEL = 'SeriesDB.series'
MODEL_VERBOSE = 'Сериал (MongoDB)'
# Поля, которые есть в форме; всё остальное в документе — «дополнительные поля»
BASE_FIELDS = ('name', 'year', 'genres', 'seasons', 'rating', 'description')

SORTS = {
    'name': [('name', ASCENDING)],
    '-year': [('year', DESCENDING), ('name', ASCENDING)],
    'year': [('year', ASCENDING), ('name', ASCENDING)],
    '-rating': [('rating', DESCENDING), ('name', ASCENDING)],
}


def series_collection():
    return _client(settings.MONGO_URI)[settings.MONGO_SERIES_DB]['series']


# ---- функции из методички ЛР6 ----

def insert_document(collection, data):
    """ Function to insert a document into a collection and
    return the document's id.
    """
    return collection.insert_one(data).inserted_id


def find_document(collection, elements, multiple=False, sort=None):
    """ Function to retrieve single or multiple documents from a provided
    Collection using a dictionary containing a document's elements.
    """
    if multiple:
        results = collection.find(elements)
        if sort:
            results = results.sort(sort)
        return [r for r in results]
    else:
        return collection.find_one(elements)


def update_document(collection, query_elements, new_values, unset_fields=()):
    """ Function to update a single document in a collection.
    """
    update = {'$set': new_values}
    if unset_fields:
        update['$unset'] = {field: '' for field in unset_fields}
    collection.update_one(query_elements, update)


def delete_document(collection, query):
    """ Function to delete a single document from a collection.
    """
    collection.delete_one(query)


# ---- поиск и запись из формы ----

def build_query(q='', genre='', year_from=None, year_to=None):
    query = {}
    if q:
        # Регистронезависимый поиск по подстроке в названии
        query['name'] = {'$regex': re.escape(q), '$options': 'i'}
    if genre:
        query['genres'] = genre            # поиск по элементу массива
    if year_from is not None or year_to is not None:
        query['year'] = {}
        if year_from is not None:
            query['year']['$gte'] = year_from
        if year_to is not None:
            query['year']['$lte'] = year_to
    return query


def all_genres():
    return sorted(g for g in series_collection().distinct('genres') if g)


def get(series_id):
    try:
        return find_document(series_collection(), {'_id': ObjectId(series_id)})
    except Exception:  # неверный ObjectId
        return None


def extra_fields(doc):
    return {k: v for k, v in doc.items() if k != '_id' and k not in BASE_FIELDS}


def create(data):
    coll = series_collection()
    new_id = insert_document(coll, data)
    log_document_event('create', MODEL, MODEL_VERBOSE, str(new_id), data['name'], data=_plain(data))
    return new_id


def update(series_id, data):
    coll = series_collection()
    old = get(series_id)
    removed = [k for k in old if k != '_id' and k not in data]
    update_document(coll, {'_id': old['_id']}, data, unset_fields=removed)
    changes = {k: {'old': old.get(k), 'new': data.get(k)}
               for k in set(data) | set(removed) if old.get(k) != data.get(k)}
    if changes:
        log_document_event('update', MODEL, MODEL_VERBOSE, series_id, data['name'], changes=_plain(changes))


def delete(series_id):
    old = get(series_id)
    delete_document(series_collection(), {'_id': old['_id']})
    log_document_event('delete', MODEL, MODEL_VERBOSE, series_id, old.get('name', ''),
                       data=_plain(extra_fields(old) | {k: old[k] for k in BASE_FIELDS if k in old}))


def _plain(value):
    """Списки жанров в журнале показываем строкой."""
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return ', '.join(map(str, value))
    return value
