#!/bin/sh
set -e

if [ "${DB_ENGINE:-postgres}" != "sqlite" ]; then
  # Ждём, пока БД начнёт принимать соединения (POSTGRES_* или DATABASE_URL)
  until python manage.py check --database default >/dev/null 2>&1; do
    echo "Waiting for database..."
    sleep 1
  done
  # В Swarm миграции делает отдельный сервис, реплики web их пропускают
  if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
    # Данные CRM из docker/sqlite_dump.json — только в пустую БД (повторно не грузим)
    if [ "${LOAD_INITIAL_DATA:-0}" = "1" ] && python manage.py shell -c \
        "import sys; from nariad.models import Nariad; sys.exit(1 if Nariad.objects.exists() else 0)"; then
      echo "БД пустая — загружаю docker/sqlite_dump.json"
      python manage.py loaddata docker/sqlite_dump.json
    fi
  fi
  python manage.py collectstatic --noinput
fi

exec "$@"
