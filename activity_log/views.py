import datetime
import json
from urllib.parse import urlencode

from bson import ObjectId, json_util
from bson.errors import InvalidId
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from .mongo import COLLECTION, collection, enabled

PAGE_SIZE = 50
ACTIONS = {'create': 'Создание', 'update': 'Изменение', 'delete': 'Удаление'}


def _unavailable(request, error=None):
    return render(request, 'activity_log/unavailable.html', {
        'page_title': 'Журнал действий',
        'error': error,
        'configured': enabled(),
    }, status=503 if error else 200)


def mongo_view(view):
    """Если MongoDB не настроена или недоступна — понятная страница вместо 500."""
    def wrapper(request, *args, **kwargs):
        if not enabled():
            return _unavailable(request)
        try:
            return view(request, *args, **kwargs)
        except PyMongoError as e:
            return _unavailable(request, e)
    wrapper.__name__ = view.__name__
    return wrapper


def _parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _event(doc):
    doc['id'] = str(doc.pop('_id'))
    doc['action_label'] = ACTIONS.get(doc.get('action'), doc.get('action'))
    return doc


@mongo_view
def journal(request):
    coll = collection()
    params = request.GET
    query = {}
    if params.get('model'):
        query['model'] = params['model']
    if params.get('action') in ACTIONS:
        query['action'] = params['action']
    if params.get('object_id'):
        object_id = params['object_id']
        query['object_id'] = int(object_id) if object_id.isdigit() else object_id
    if params.get('q'):
        query['$text'] = {'$search': params['q']}
    tz = timezone.get_current_timezone()
    date_from, date_to = _parse_date(params.get('from')), _parse_date(params.get('to'))
    if date_from or date_to:
        query['timestamp'] = {}
        if date_from:
            query['timestamp']['$gte'] = datetime.datetime.combine(date_from, datetime.time.min, tz)
        if date_to:
            query['timestamp']['$lt'] = datetime.datetime.combine(date_to + datetime.timedelta(days=1),
                                                                  datetime.time.min, tz)

    try:
        page = max(int(params.get('page', 1)), 1)
    except ValueError:
        page = 1
    total = coll.count_documents(query)
    events = [_event(d) for d in coll.find(query).sort('timestamp', DESCENDING)
              .skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)]

    models = [{'label': m['_id'], 'verbose': m['verbose']} for m in coll.aggregate([
        {'$group': {'_id': '$model', 'verbose': {'$first': '$model_verbose'}}},
        {'$sort': {'verbose': 1}},
    ])]
    filters = {k: v for k, v in params.items() if k != 'page' and v}
    return render(request, 'activity_log/journal.html', {
        'page_title': 'Журнал действий',
        'events': events,
        'total': total,
        'page': page,
        'prev_url': f'?{urlencode({**filters, "page": page - 1})}' if page > 1 else None,
        'next_url': f'?{urlencode({**filters, "page": page + 1})}' if page * PAGE_SIZE < total else None,
        'models': models,
        'actions': ACTIONS,
        'f': params,
        'query_json': json_util.dumps(query, ensure_ascii=False, json_options=json_util.RELAXED_JSON_OPTIONS),
    })


@mongo_view
def event_detail(request, event_id):
    try:
        doc = collection().find_one({'_id': ObjectId(event_id)})
    except InvalidId:
        doc = None
    if doc is None:
        raise Http404('Событие не найдено')
    raw = json_util.dumps(doc, indent=2, ensure_ascii=False, json_options=json_util.RELAXED_JSON_OPTIONS)
    return render(request, 'activity_log/detail.html', {
        'page_title': 'Журнал действий',
        'e': _event(doc),
        'raw': raw,
    })


@mongo_view
def stats(request):
    coll = collection()
    since = timezone.now() - datetime.timedelta(days=14)
    pipelines = {
        'by_model': [
            {'$group': {'_id': '$model_verbose', 'count': {'$sum': 1}, 'last': {'$max': '$timestamp'}}},
            {'$sort': {'count': -1}},
        ],
        'by_action': [
            {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ],
        'by_day': [
            {'$match': {'timestamp': {'$gte': since}}},
            {'$group': {'_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp',
                                                  'timezone': settings.TIME_ZONE}},
                        'count': {'$sum': 1}}},
            {'$sort': {'_id': 1}},
        ],
        'top_objects': [
            {'$group': {'_id': {'model': '$model', 'object_id': '$object_id'},
                        'model_verbose': {'$last': '$model_verbose'},
                        'object_repr': {'$last': '$object_repr'},
                        'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10},
        ],
    }
    results = {name: list(coll.aggregate(pipeline)) for name, pipeline in pipelines.items()}
    # В шаблонах Django нельзя обратиться к ключу «_id» — переименовываем
    for rows in results.values():
        for row in rows:
            row['key'] = row.pop('_id')
    for row in results['by_action']:
        row['label'] = ACTIONS.get(row['key'], row['key'])
    max_day = max([d['count'] for d in results['by_day']], default=1)
    for row in results['by_day']:
        row['percent'] = round(row['count'] * 100 / max_day)

    coll_stats = coll.database.command('collStats', COLLECTION)
    return render(request, 'activity_log/stats.html', {
        'page_title': 'Журнал действий',
        'r': results,
        'pipelines': {name: json_util.dumps(p, indent=2, ensure_ascii=False,
                                            json_options=json_util.RELAXED_JSON_OPTIONS)
                      for name, p in pipelines.items()},
        'coll_stats': {
            'count': coll_stats.get('count', 0),
            'size': coll_stats.get('size', 0),
            'storage': coll_stats.get('storageSize', 0),
            'indexes': coll_stats.get('nindexes', 0),
        },
        'indexes': [{'name': name, 'key': json.dumps(info['key'], ensure_ascii=False)}
                    for name, info in coll.index_information().items()],
        'server_version': coll.database.client.server_info()['version'],
        'db_name': coll.database.name,
    })
