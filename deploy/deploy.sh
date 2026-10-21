#!/usr/bin/env bash
# Выкладка CRM на удалённый сервер по SSH (на сервере нужен Docker с плагином compose).
#
#   ./deploy/deploy.sh user@host [опции]
#
# Опции:
#   --dir DIR        каталог на сервере (по умолчанию crm, относительно домашнего)
#   --port N         порт сайта (WEB_PORT), например 80 или 8080
#   --db-port N      внешний порт PostgreSQL (DB_PORT)
#   --load-data      загрузить в БД данные из docker/sqlite_dump.json (первый запуск)
#
# Перед запуском проверяется, что порты на сервере свободны; если нет — деплой
# останавливается и показывает, какой порт занят.
#
# Переменные окружения:
#   SSH_PORT=2222    нестандартный порт SSH
#   SSH_OPTS="-i ~/.ssh/key"  дополнительные опции ssh
#   ENV_FILE=...     локальный файл с настройками сервера (по умолчанию .env.server);
#                    если он есть — копируется на сервер как .env
set -euo pipefail
cd "$(dirname "$0")/.."

usage() { sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TARGET=""
DIR=crm
WEB_PORT=""
DB_PORT=""
LOAD_DATA=0
while [ $# -gt 0 ]; do
  case "$1" in
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

ENV_FILE=${ENV_FILE:-.env.server}
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
  echo "==> Копирую $ENV_FILE в ~/$DIR/.env"
  "${SSH[@]}" "cat > '$DIR/.env'" < "$ENV_FILE"
elif "${SSH[@]}" "test -f '$DIR/.env'"; then
  echo "==> На сервере уже есть .env — оставляю его"
else
  echo "==> Создаю .env из .env.example (поменяйте пароли и DJANGO_SECRET_KEY!)"
  "${SSH[@]}" "cp '$DIR/.env.example' '$DIR/.env'"
fi

set_env() {  # set_env KEY VALUE — заменить или добавить строку в .env на сервере
  "${SSH[@]}" "cd '$DIR' && (grep -q '^$1=' .env && sed -i 's|^$1=.*|$1=$2|' .env || echo '$1=$2' >> .env)"
}
[ -n "$WEB_PORT" ] && set_env WEB_PORT "$WEB_PORT"
[ -n "$DB_PORT" ] && set_env DB_PORT "$DB_PORT"

echo "==> Проверяю, свободны ли порты на сервере"
if ! "${SSH[@]}" "cd '$DIR' && bash deploy/ports.sh"; then
  echo "Деплой остановлен. Укажите выделенные вам порты: --port N / --db-port N (или в .env.server)."
  exit 1
fi

echo "==> Собираю и запускаю контейнеры"
"${SSH[@]}" "cd '$DIR' && docker compose up -d --build --remove-orphans --wait"

if [ "$LOAD_DATA" = 1 ]; then
  echo "==> Загружаю данные из docker/sqlite_dump.json"
  "${SSH[@]}" "cd '$DIR' && docker compose exec -T web python manage.py loaddata docker/sqlite_dump.json"
fi

"${SSH[@]}" "cd '$DIR' && docker compose ps"
PORT=$("${SSH[@]}" "grep -E '^WEB_PORT=' '$DIR/.env' | cut -d= -f2" || true)
HOST=${TARGET#*@}
echo
echo "Готово: http://$HOST:${PORT:-8000}/nariad/   Dropbox: http://$HOST:${PORT:-8000}/dropbox/"
