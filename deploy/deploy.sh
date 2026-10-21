#!/usr/bin/env bash
# Выкладка на удалённый сервер по SSH (на сервере нужен Docker с плагином compose).
#
#   ./deploy/deploy.sh user@host [опции]
#
# Опции:
#   --stack S        что запускать: . — CRM (по умолчанию), lab6_mongodb, lab7_wordpress
#   --dir DIR        каталог на сервере (по умолчанию crm, относительно домашнего)
#   --port N         порт сайта CRM (WEB_PORT), только для --stack .
#   --db-port N      внешний порт PostgreSQL CRM (DB_PORT), только для --stack .
#   --load-data      загрузить в БД CRM данные из docker/sqlite_dump.json (первый запуск)
#
# Перед запуском проверяется, что порты на сервере свободны; если нет — деплой
# останавливается и показывает, какой порт занят.
#
# Переменные окружения:
#   SSH_PORT=2222    нестандартный порт SSH
#   SSH_OPTS="-i ~/.ssh/key"  дополнительные опции ssh
#   ENV_FILE=...     локальный файл с настройками сервера (по умолчанию <stack>/.env.server);
#                    если он есть — копируется на сервер как <stack>/.env
set -euo pipefail
cd "$(dirname "$0")/.."

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TARGET=""
DIR=crm
STACK=.
WEB_PORT=""
DB_PORT=""
LOAD_DATA=0
while [ $# -gt 0 ]; do
  case "$1" in
    --stack) STACK=${2%/}; shift 2 ;;
    --dir) DIR=$2; shift 2 ;;
    --port) WEB_PORT=$2; shift 2 ;;
    --db-port) DB_PORT=$2; shift 2 ;;
    --load-data) LOAD_DATA=1; shift ;;
    -h|--help) usage ;;
    -*) echo "Неизвестная опция: $1"; usage ;;
    *) TARGET=$1; shift ;;
  esac
done
[ -n "$TARGET" ] || usage
[ -f "$STACK/docker-compose.yml" ] || { echo "Нет $STACK/docker-compose.yml"; exit 1; }
if [ "$STACK" != . ] && { [ -n "$WEB_PORT$DB_PORT" ] || [ "$LOAD_DATA" = 1 ]; }; then
  echo "--port, --db-port и --load-data относятся только к CRM; порты $STACK задаются в $STACK/.env.server"
  exit 1
fi

ENV_FILE=${ENV_FILE:-$STACK/.env.server}
REMOTE="$DIR/$STACK"
# shellcheck disable=SC2206
SSH=(ssh -p "${SSH_PORT:-22}" ${SSH_OPTS:-} "$TARGET")

echo "==> Проверяю Docker на $TARGET"
if ! "${SSH[@]}" "docker compose version" >/dev/null; then
  echo "На сервере не найден 'docker compose'. Установите Docker:"
  echo "  curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker \$USER"
  exit 1
fi

echo "==> Копирую проект в ~/$DIR"
git ls-files -z -co --exclude-standard \
  | tar --null -T - -czf - \
  | "${SSH[@]}" "mkdir -p '$DIR' && tar -xzf - -C '$DIR'"

if [ -f "$ENV_FILE" ]; then
  # Пустые значения (например, пароли, сгенерированные на сервере при первом запуске)
  # берутся из уже существующего .env на сервере, чтобы не потерять их при передеплое
  echo "==> Копирую $ENV_FILE в ~/$REMOTE/.env (пустые значения берутся из текущего .env сервера)"
  tr -d '\r' < "$ENV_FILE" | "${SSH[@]}" "cd '$REMOTE' && cat > .env.new && if [ -s .env ]; then awk '
      FILENAME == ARGV[1] { i = index(\$0, \"=\"); if (i) old[substr(\$0, 1, i - 1)] = substr(\$0, i + 1); next }
      { i = index(\$0, \"=\"); k = substr(\$0, 1, i - 1)
        if (i && substr(\$0, i + 1) == \"\" && old[k] != \"\") { print k \"=\" old[k]; next }
        print }' .env .env.new > .env.merged && mv .env.merged .env && rm -f .env.new; else mv .env.new .env; fi"
elif "${SSH[@]}" "test -f '$REMOTE/.env'"; then
  echo "==> На сервере уже есть $REMOTE/.env — оставляю его"
elif "${SSH[@]}" "test -f '$REMOTE/.env.example'"; then
  echo "==> Создаю $REMOTE/.env из .env.example (проверьте порты и пароли!)"
  "${SSH[@]}" "cp '$REMOTE/.env.example' '$REMOTE/.env'"
fi

set_env() {  # set_env KEY VALUE — заменить или добавить строку в .env на сервере
  "${SSH[@]}" "cd '$REMOTE' && (grep -q '^$1=' .env && sed -i 's|^$1=.*|$1=$2|' .env || echo '$1=$2' >> .env)"
}
[ -n "$WEB_PORT" ] && set_env WEB_PORT "$WEB_PORT"
[ -n "$DB_PORT" ] && set_env DB_PORT "$DB_PORT"

echo "==> Проверяю, свободны ли порты на сервере"
if ! "${SSH[@]}" "cd '$DIR' && bash deploy/ports.sh '$STACK'"; then
  echo "Деплой остановлен. Впишите выделенные вам порты в $ENV_FILE (для CRM можно --port / --db-port)."
  exit 1
fi

if [ -f "$STACK/setup.sh" ]; then
  echo "==> Запускаю $STACK/setup.sh"
  "${SSH[@]}" "cd '$REMOTE' && bash setup.sh"
else
  echo "==> Собираю и запускаю контейнеры"
  "${SSH[@]}" "cd '$REMOTE' && docker compose up -d --build --remove-orphans --wait"
fi

if [ "$LOAD_DATA" = 1 ]; then
  echo "==> Загружаю данные из docker/sqlite_dump.json"
  "${SSH[@]}" "cd '$REMOTE' && docker compose exec -T web python manage.py loaddata docker/sqlite_dump.json"
fi

"${SSH[@]}" "cd '$REMOTE' && docker compose ps"
if [ "$STACK" = . ]; then
  PORT=$("${SSH[@]}" "grep -E '^WEB_PORT=' '$REMOTE/.env' | cut -d= -f2 | tr -d '\r'" || true)
  HOST=${TARGET#*@}
  echo
  echo "Готово: http://$HOST:${PORT:-8000}/nariad/   Dropbox: http://$HOST:${PORT:-8000}/dropbox/"
fi
