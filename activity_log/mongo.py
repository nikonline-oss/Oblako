"""Подключение к MongoDB и запись событий журнала через PyMongo."""
import datetime
import decimal
import logging
from functools import lru_cache

from django.conf import settings
from django.db import models
from django.utils import timezone
from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient
from pymongo.errors import PyMongoError

from .middleware import current_request

logger = logging.getLogger(__name__)

COLLECTION = 'activity'
_indexed_databases = set()


def enabled():
    return bool(settings.MONGO_URI)


@lru_cache(maxsize=4)
def _client(uri):
    # Короткий таймаут: если MongoDB недоступна, CRM не должна «зависать» на сохранении
    return MongoClient(uri, serverSelectionTimeoutMS=2000, tz_aware=True)


def collection():
    db_name = settings.MONGO_DB
    coll = _client(settings.MONGO_URI)[db_name][COLLECTION]
    if db_name not in _indexed_databases:
        coll.create_index([('timestamp', DESCENDING)], name='by_time')
        coll.create_index([('model', ASCENDING), ('object_id', ASCENDING), ('timestamp', DESCENDING)],
                          name='by_object')
        # Полнотекстовый поиск с русской морфологией: «наряды» найдёт «наряд»
        coll.create_index([('object_repr', TEXT), ('model_verbose', TEXT), ('search_text', TEXT)],
                          name='text_search', default_language='russian')
        _indexed_databases.add(db_name)
    return coll


def to_bson(value):
    """Значение поля модели → тип, который понимает BSON."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    return str(value)


def snapshot(instance):
    """Документ с текущими значениями полей объекта. Внешние ключи — {id, repr}."""
    data = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key:
            continue
        if isinstance(field, models.ForeignKey):
            fk_id = getattr(instance, field.attname)
            related = getattr(instance, field.name, None) if fk_id is not None else None
            data[field.name] = {'id': fk_id, 'repr': str(related)} if fk_id is not None else None
        else:
            data[field.name] = to_bson(getattr(instance, field.attname))
    return data


def _search_text(data):
    parts = []
    for value in data.values():
        if isinstance(value, dict):
            parts.append(str(value.get('repr') or value.get('new') or ''))
        elif isinstance(value, str):
            parts.append(value)
    return ' '.join(parts)


def log_event(action, instance, data=None, changes=None):
    """Событие для объекта модели Django."""
    meta = instance._meta
    log_document_event(action, meta.label, str(meta.verbose_name), instance.pk, str(instance),
                       data=data, changes=changes)


def log_document_event(action, model, model_verbose, object_id, object_repr, data=None, changes=None):
    """Пишет событие в коллекцию activity. Ошибки MongoDB не ломают работу CRM."""
    request = current_request()
    user = None
    ip = None
    if request is not None:
        if getattr(request, 'user', None) is not None and request.user.is_authenticated:
            user = request.user.get_username()
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')

    document = {
        'timestamp': timezone.now(),
        'action': action,
        'model': model,
        'model_verbose': model_verbose,
        'object_id': object_id,
        'object_repr': str(object_repr)[:300],
        'user': user,
        'ip': ip,
        'path': request.path if request is not None else None,
    }
    if data is not None:
        document['data'] = data
        document['search_text'] = _search_text(data)
    if changes is not None:
        document['changes'] = changes
        document['search_text'] = _search_text({k: v['new'] for k, v in changes.items()})

    try:
        collection().insert_one(document)
    except PyMongoError as e:
        logger.warning('Журнал MongoDB недоступен, событие не записано: %s', e)
