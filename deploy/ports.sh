#!/usr/bin/env bash
# Проверяет, что порты, которые займёт проект, свободны на этой машине.
# Порты берутся из `docker compose config`, т.е. уже с учётом .env и COMPOSE_PROFILES.
# Ничего не меняет: при конфликте выводит занятые порты и выходит с кодом 1.
# Порт считается своим (не конфликтом), если его уже держит этот же compose-проект.
#
#   ./deploy/ports.sh                                   — порты docker-compose.yml
#   ./deploy/ports.sh --also swarm=80 --also registry=5000   — плюс дополнительные
#   ./deploy/ports.sh --no-compose --also swarm=80      — только дополнительные
set -euo pipefail
cd "$(dirname "$0")/.."

EXTRA=""
USE_COMPOSE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --also) EXTRA="$EXTRA${2%%=*} ${2#*=}"$'\n'; shift 2 ;;
    --no-compose) USE_COMPOSE=0; shift ;;
    *) echo "Неизвестный аргумент: $1"; exit 2 ;;
  esac
done

# "сервис порт" для всех опубликованных портов
published() {
  docker compose config 2>/dev/null | awk '
    /^services:/ { s = 1; next }
    /^[a-z]/     { s = 0 }
    s && /^  [^ ].*:$/ { svc = $1; sub(":", "", svc) }
    s && /published:/  { gsub(/[^0-9]/, "", $2); print svc, $2 }'
}

# Слушаемые порты (ss / netstat Linux и Windows) + опубликованные Docker-ом
listening() {
  { ss -Hltn 2>/dev/null || netstat -an 2>/dev/null | grep -i listen || true; } \
    | awk '{for (i = 1; i <= NF; i++) if ($i ~ /[:.][0-9]+$/) { print $i; break }}' \
    | sed 's/.*[:.]//'
  docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE '[0-9]+->' | tr -d '>-' || true
}
own_ports() { docker compose ps --format '{{.Ports}}' 2>/dev/null | grep -oE '[0-9]+->' | tr -d '>-' || true; }

PORTS=""
if [ $USE_COMPOSE = 1 ]; then
  PORTS=$(published)
  [ -n "$PORTS" ] || { echo "Не удалось прочитать порты из docker compose config (есть ли .env?)"; exit 1; }
  OWN=$(own_ports | sort -un)
else
  OWN=""
fi
PORTS=$(printf '%s\n%s' "$PORTS" "$EXTRA" | sed '/^$/d')
BUSY=$(listening | sort -un)
in_list() { printf '%s\n' $2 | grep -qx "$1"; }

conflicts=0
while read -r svc port; do
  if in_list "$port" "$OWN"; then
    echo "  $port ($svc) — уже используется этим проектом"
  elif in_list "$port" "$BUSY"; then
    echo "  $port ($svc) — ЗАНЯТ другим процессом"
    conflicts=$((conflicts + 1))
  else
    echo "  $port ($svc) — свободен"
  fi
done <<< "$PORTS"

if [ $conflicts -gt 0 ]; then
  echo "Есть занятые порты — впишите в .env порты, выделенные вам на сервере."
  exit 1
fi
