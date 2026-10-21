import socket

from django.db import connection
from django.http import JsonResponse


def swarm_info(request):
    """Какая реплика обработала запрос и что вернула БД (для демонстрации Swarm)."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT version(), now(), inet_server_addr()')
        db_version, db_time, db_addr = cursor.fetchone()
        cursor.execute('SELECT count(*) FROM nariad_nariad')
        nariad_count = cursor.fetchone()[0]
        cursor.execute('SELECT count(*) FROM employees_employee')
        employee_count = cursor.fetchone()[0]

    return JsonResponse({
        'web_container': socket.gethostname(),
        'web_ip': socket.gethostbyname(socket.gethostname()),
        'db_host': connection.settings_dict['HOST'],
        'db_ip': str(db_addr),
        'db_version': db_version.split(',')[0],
        'db_time': db_time.isoformat(),
        'nariad_count': nariad_count,
        'employee_count': employee_count,
    }, json_dumps_params={'ensure_ascii': False, 'indent': 2})
