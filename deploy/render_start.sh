#!/usr/bin/env bash
# Команда запуска сайта на Render (render.yaml → startCommand).
# На бесплатном тарифе нет pre-deploy команд и консоли, поэтому миграции и
# первичная загрузка данных (LOAD_INITIAL_DATA) выполняются здесь, перед стартом
# gunicorn — той же логикой, что и в Docker (docker/entrypoint.sh).
set -euo pipefail
cd "$(dirname "$0")/.."

exec sh docker/entrypoint.sh gunicorn crm.wsgi:application --timeout 300
