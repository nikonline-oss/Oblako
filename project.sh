#!/usr/bin/env bash
# Управление всем проектом: CRM + MongoDB + WordPress (+ Swarm-ферма ЛР3).
#
#   ./project.sh up            — подготовить .env, проверить порты, собрать и запустить всё,
#                                установить и наполнить WordPress (при первом запуске)
#   ./project.sh status        — состояние контейнеров и адреса всех лаб
#   ./project.sh urls          — только адреса
#   ./project.sh lab6          — демонстрация ЛР6: Mongo Shell и скрипт PyMongo
#   ./project.sh swarm up|down|status — Swarm-ферма ЛР3
#   ./project.sh logs [сервис] — логи (Ctrl+C — выход)
#   ./project.sh down          — остановить всё (данные сохраняются)
#   ./project.sh wp-reset      — удалить сайт WordPress с его БД и собрать заново
#
# Все порты, адрес и пароли — в .env (создаётся из .env.example).
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"

usage() { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

# ---------- .env ----------
get_env() { [ -f .env ] && grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '\r' || true; }
set_env() {
  if grep -qE "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
gen_secret() { head -c 96 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "${1:-24}"; }

prepare_env() {
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан .env из .env.example"
  fi
  # Новые переменные из .env.example, которых ещё нет в .env
  local added=0 key
  while IFS= read -r line; do
    key=${line%%=*}
    if ! grep -qE "^$key=" .env; then echo "$line" >> .env; added=$((added + 1)); fi
  done < <(tr -d '\r' < .env.example | grep -E '^[A-Z_]+=')
  [ $added -eq 0 ] || echo "В .env добавлено новых переменных: $added"
  # Если база уже создана, её пароль генерировать нельзя: новый не подойдёт к существующей БД
  local volume
  for pair in POSTGRES_PASSWORD:crm_pgdata MYSQL_PASSWORD:crm_wp-dbdata MYSQL_ROOT_PASSWORD:crm_wp-dbdata \
              WP_ADMIN_PASSWORD:crm_wp-dbdata; do
    key=${pair%%:*}; volume=${pair#*:}
    if [ -z "$(get_env "$key")" ] && docker volume inspect "$volume" >/dev/null 2>&1; then
      echo "ОШИБКА: в .env пустой $key, а база (том $volume) уже создана со старым паролем."
      echo "Верните прежнее значение $key в .env. Или удалите базу: docker volume rm $volume (данные пропадут)."
      exit 1
    fi
  done
  # Пустые пароли и ключи генерируем (уже заданные не трогаем!)
  for key in POSTGRES_PASSWORD MYSQL_PASSWORD MYSQL_ROOT_PASSWORD WP_ADMIN_PASSWORD; do
    [ -n "$(get_env $key)" ] || set_env "$key" "$(gen_secret 20)"
  done
  case "$(get_env DJANGO_SECRET_KEY)" in ''|change-me) set_env DJANGO_SECRET_KEY "$(gen_secret 50)" ;; esac
}

wp_url() {
  local url
  url=$(get_env WP_URL)
  echo "${url:-http://$(get_env PUBLIC_HOST):$(get_env WP_PORT)}"
}

# ---------- WordPress ----------
wp_cli() { docker compose run --rm -T wp-cli "$@"; }

wp_seed() {
  echo "==> WordPress: установка и наполнение (если ещё не сделано)"
  wp_cli bash /setup/seed.sh
  # Если сайт переехал (другой PUBLIC_HOST/WP_PORT) — переписываем адреса в БД
  local old new
  new=$(wp_url)
  old=$(wp_cli wp eval 'global $wpdb; echo $wpdb->get_var("SELECT option_value FROM $wpdb->options WHERE option_name = '"'"'home'"'"'");' | tr -d '\r')
  if [ -n "$old" ] && [ "$old" != "$new" ]; then
    echo "==> WordPress: адрес сайта $old → $new"
    wp_cli wp search-replace "$old" "$new" --all-tables --skip-columns=guid
  fi
}

# ---------- Адреса ----------
urls() {
  local host web wp pma
  host=$(get_env PUBLIC_HOST); host=${host:-localhost}
  web="http://$host:$(get_env WEB_PORT)"
  wp=$(wp_url)
  pma="http://$( [ "$(get_env PMA_BIND)" = 127.0.0.1 ] && echo localhost || echo "$host" ):$(get_env PMA_PORT)"
  cat <<EOF

  ЛР2  CRM в Docker            $web/nariad/
  ЛР4  Dropbox                 $web/dropbox/
  ЛР5  версия/релиз (JSON)     $web/
  ЛР6  MongoDB: CRUD, журнал   $web/journal/series/      демо в консоли: ./project.sh lab6
  ЛР7  WordPress               $wp/
       Консоль WordPress       $wp/wp-admin/      логин/пароль: WP_ADMIN_USER / WP_ADMIN_PASSWORD в .env
       phpMyAdmin              $pma/      пользователь: MYSQL_USER / MYSQL_PASSWORD в .env
  ЛР3  Swarm-ферма             http://$host:$(get_env SWARM_HTTP_PORT)/   (./project.sh swarm up)
EOF
}

# ---------- Команды ----------
up() {
  prepare_env
  echo "==> Проверяю порты"
  ./deploy/ports.sh
  echo "==> Собираю и запускаю контейнеры"
  WP_URL=$(wp_url) docker compose up -d --build --remove-orphans --wait
  # Порты БД выключены в .env — убираем пробросы, если они остались от прошлого запуска
  if ! grep -qE '^COMPOSE_PROFILES=.*db-ports' .env; then
    docker compose --profile db-ports rm -sf pg-port mongo-port >/dev/null 2>&1 || true
  fi
  WP_URL=$(wp_url) wp_seed
  echo
  echo "Готово. Адреса:"
  urls
}

lab6() {
  echo "==> ЛР6, шаг 2: connectionStatus"
  docker compose exec -T mongo mongo --eval 'db.runCommand({ connectionStatus: 1 })'
  echo
  echo "==> ЛР6: Mongo Shell (lab6_mongodb/shell_demo.js)"
  docker compose exec -T mongo mongo --quiet /lab/shell_demo.js
  echo
  echo "==> ЛР6: PyMongo (lab6_mongodb/mongo_db_script.py)"
  docker compose run --rm --build lab6-script
}

swarm() {
  case "${1:-status}" in
    up)
      prepare_env
      ./deploy/ports.sh --no-compose --also "swarm=$(get_env SWARM_HTTP_PORT)" --also "registry=$(get_env REGISTRY_PORT)"
      ./swarm/cluster.sh up ;;
    down|status) ./swarm/cluster.sh "$1" ;;
    *) usage ;;
  esac
}

case "${1:-}" in
  up) up ;;
  status) docker compose ps; urls ;;
  urls) urls ;;
  lab6) lab6 ;;
  swarm) swarm "${2:-status}" ;;
  logs) shift; docker compose logs -f "$@" ;;
  down) docker compose stop ;;
  wp-reset)
    docker compose rm -sf wordpress wp-db phpmyadmin
    docker volume rm -f crm_wpdata crm_wp-dbdata
    up ;;
  *) usage ;;
esac
