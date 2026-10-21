import os
import socket

from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def _host_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:  # на Heroku имя dyno может не резолвиться
        return None


def swarm_info(request):
    """Версия приложения, кто обработал запрос и что вернула БД (Swarm, Heroku)."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT version(), now(), inet_server_addr()')
        db_version, db_time, db_addr = cursor.fetchone()
        cursor.execute('SELECT count(*) FROM nariad_nariad')
        nariad_count = cursor.fetchone()[0]
        cursor.execute('SELECT count(*) FROM employees_employee')
        employee_count = cursor.fetchone()[0]

    return JsonResponse({
        'app_version': settings.APP_VERSION,
        'heroku_release': os.environ.get('HEROKU_RELEASE_VERSION'),
        'web_container': os.environ.get('DYNO') or socket.gethostname(),
        'web_ip': _host_ip(),
        'db_host': connection.settings_dict['HOST'],
        'db_ip': str(db_addr),
        'db_version': db_version.split(',')[0],
        'db_time': db_time.isoformat(),
        'nariad_count': nariad_count,
        'employee_count': employee_count,
    }, json_dumps_params={'ensure_ascii': False, 'indent': 2})
