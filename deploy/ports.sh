#!/usr/bin/env bash
# Проверяет, что порты из .env (WEB_PORT, DB_PORT) свободны на этой машине.
# Ничего не меняет: при конфликте выводит, какой порт занят, и выходит с кодом 1.
# Порт считается своим (не конфликтом), если его уже держит этот же docker compose проект.
#
#   ./deploy/ports.sh
set -euo pipefail
cd "$(dirname "$0")/.."

ENV=.env
[ -f "$ENV" ] || { echo "Нет файла $ENV (скопируйте .env.example)"; exit 1; }

# Переменная и её значение по умолчанию (как в docker-compose.yml)
PORT_VARS="WEB_PORT:8000 DB_PORT:5432"

get_env() { grep -E "^$1=" "$ENV" | tail -1 | cut -d= -f2- | tr -d '\r ' || true; }

# Слушаемые порты (ss / netstat Linux и Windows) + опубликованные Docker-ом
listening() {
  { ss -Hltn 2>/dev/null || netstat -an 2>/dev/null | grep -i listen || true; } \
    | awk '{for (i = 1; i <= NF; i++) if ($i ~ /[:.][0-9]+$/) { print $i; break }}' \
    | sed 's/.*[:.]//'
  docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE '[0-9]+->' | tr -d '>-' || true
}
own_ports() { docker compose ps --format '{{.Ports}}' 2>/dev/null | grep -oE '[0-9]+->' | tr -d '>-' || true; }

BUSY=$(listening | sort -un)
OWN=$(own_ports | sort -un)
in_list() { printf '%s\n' $2 | grep -qx "$1"; }

conflicts=0
for pair in $PORT_VARS; do
  var=${pair%%:*}
  port=$(get_env "$var")
  port=${port:-${pair##*:}}
  if in_list "$port" "$OWN"; then
    echo "  $var=$port — уже используется этим проектом"
  elif in_list "$port" "$BUSY"; then
    echo "  $var=$port — ЗАНЯТ другим процессом"
    conflicts=$((conflicts + 1))
  else
    echo "  $var=$port — свободен"
  fi
done

if [ $conflicts -gt 0 ]; then
  echo "Есть занятые порты — впишите в $ENV порты, выделенные вам на сервере."
  exit 1
fi
