#!/usr/bin/env bash
# Деплой CRM в Heroku (ЛР5). Нужны: аккаунт Heroku и Heroku CLI (heroku login).
#
#   ./deploy/heroku.sh ИМЯ_ПРИЛОЖЕНИЯ [--load-data]
#
# Первый запуск: создаёт приложение и Heroku Postgres, задаёт переменные окружения,
# добавляет git-remote "heroku" и пушит текущую ветку. Повторный запуск — просто
# новый деплой закоммиченных изменений (git push heroku).
#   --load-data   загрузить данные CRM из docker/sqlite_dump.json
#
# Тариф Postgres можно поменять: HEROKU_DB_PLAN=essential-0 (по умолчанию)
set -euo pipefail
cd "$(dirname "$0")/.."

APP=${1:-}
[ -n "$APP" ] && [ "${APP#-}" = "$APP" ] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
LOAD_DATA=0
[ "${2:-}" = "--load-data" ] && LOAD_DATA=1
DB_PLAN=${HEROKU_DB_PLAN:-essential-0}

command -v heroku >/dev/null || {
  echo "Не найден Heroku CLI. Установите: https://devcenter.heroku.com/articles/heroku-cli"
  exit 1
}
heroku auth:whoami >/dev/null 2>&1 || heroku login

if heroku apps:info -a "$APP" >/dev/null 2>&1; then
  echo "==> Приложение $APP уже есть"
else
  echo "==> Создаю приложение $APP"
  heroku create "$APP"
fi

if ! heroku addons -a "$APP" 2>/dev/null | grep -q heroku-postgresql; then
  echo "==> Подключаю Heroku Postgres ($DB_PLAN) — задаёт DATABASE_URL"
  heroku addons:create "heroku-postgresql:$DB_PLAN" -a "$APP" --wait
fi

echo "==> Настраиваю переменные окружения"
if ! heroku config:get DJANGO_SECRET_KEY -a "$APP" | grep -q .; then
  heroku config:set -a "$APP" DJANGO_SECRET_KEY="$(head -c 48 /dev/urandom | base64 | tr -d '/+=\n')" >/dev/null
fi
heroku config:set -a "$APP" \
  DJANGO_DEBUG=0 \
  DJANGO_ALLOWED_HOSTS=.herokuapp.com \
  DJANGO_CSRF_TRUSTED_ORIGINS='https://*.herokuapp.com' >/dev/null
DROPBOX_APP_KEY=$( [ -f .env ] && grep -E '^DROPBOX_APP_KEY=' .env | cut -d= -f2- | tr -d '\r' || true)
[ -n "$DROPBOX_APP_KEY" ] && heroku config:set -a "$APP" DROPBOX_APP_KEY="$DROPBOX_APP_KEY" >/dev/null
# Номер релиза Heroku в HEROKU_RELEASE_VERSION — его показывает главная страница
heroku labs:enable runtime-dyno-metadata -a "$APP" >/dev/null 2>&1 || true

heroku git:remote -a "$APP" >/dev/null
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "!! Есть незакоммиченные изменения — в Heroku уйдёт только то, что закоммичено."
fi

echo "==> git push heroku $(git branch --show-current):main"
git push heroku HEAD:main

if [ "$LOAD_DATA" = 1 ]; then
  echo "==> Загружаю данные CRM"
  heroku run -a "$APP" python manage.py loaddata docker/sqlite_dump.json
fi

heroku ps -a "$APP"
URL=$(heroku apps:info -a "$APP" -s | grep '^web_url=' | cut -d= -f2-)
echo
echo "Готово: ${URL} (CRM: ${URL}nariad/, Dropbox: ${URL}dropbox/)"
