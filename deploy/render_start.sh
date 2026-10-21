#!/usr/bin/env bash
# Команда запуска сайта на Render (render.yaml → startCommand).
# На бесплатном тарифе нет pre-deploy команд и консоли, поэтому миграции и
# первичная загрузка данных выполняются здесь, перед стартом gunicorn.
set -euo pipefail
cd "$(dirname "$0")/.."

python manage.py migrate --noinput

if [ "${LOAD_INITIAL_DATA:-0}" = "1" ]; then
  # Код выхода 0 — нарядов нет, БД пустая: загружаем данные CRM
  if python manage.py shell -c "import sys; from nariad.models import Nariad; sys.exit(1 if Nariad.objects.exists() else 0)"; then
    echo "БД пустая — загружаю docker/sqlite_dump.json"
    python manage.py loaddata docker/sqlite_dump.json
  fi
fi

# gunicorn слушает $PORT, который выдаёт Render
exec gunicorn crm.wsgi:application --timeout 300
