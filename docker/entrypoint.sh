#!/bin/sh
set -e

# Ждём, пока PostgreSQL начнёт принимать соединения
if [ "${DB_ENGINE:-postgres}" != "sqlite" ]; then
  until python -c "import psycopg, os; psycopg.connect(host=os.environ['POSTGRES_HOST'], port=os.environ.get('POSTGRES_PORT', '5432'), dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD']).close()" 2>/dev/null; do
    echo "Waiting for PostgreSQL..."
    sleep 1
  done
  # В Swarm миграции делает отдельный сервис, реплики web их пропускают
  if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
  fi
  python manage.py collectstatic --noinput
fi

exec "$@"
