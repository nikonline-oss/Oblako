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
  fi
  python manage.py collectstatic --noinput
fi

exec "$@"
