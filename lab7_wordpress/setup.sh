#!/usr/bin/env bash
# ЛР7: WordPress в Docker.
#
#   ./setup.sh            — запустить и (при первом запуске) установить и наполнить сайт
#   ./setup.sh url URL    — сменить адрес сайта, например http://1.2.3.4:18081
#                           (после смены WP_PORT или переноса на сервер)
#   ./setup.sh reset      — удалить сайт вместе с БД и собрать заново
#   ./setup.sh down       — остановить (данные сохраняются)
#
# Порты, адрес и пароли — в .env. При первом запуске .env создаётся из .env.example,
# пароли MySQL и администратора генерируются и записываются туда же.
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")"

get_env() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '\r' || true; }
set_env() {
  if grep -qE "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
gen_password() { head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20; }

prepare_env() {
  [ -f .env ] || { cp .env.example .env; echo "Создан .env из .env.example"; }
  for key in MYSQL_PASSWORD MYSQL_ROOT_PASSWORD WP_ADMIN_PASSWORD; do
    [ -n "$(get_env $key)" ] || set_env "$key" "$(gen_password)"
  done
}

up() {
  prepare_env
  ../deploy/ports.sh . || exit 1
  docker compose up -d --wait
  docker compose run --rm cli bash /setup/seed.sh
  echo
  echo "Сайт:       $(get_env WP_URL)/"
  echo "Админка:    $(get_env WP_URL)/wp-admin/  (логин и пароль — WP_ADMIN_USER / WP_ADMIN_PASSWORD в lab7_wordpress/.env)"
  echo "phpMyAdmin: http://localhost:$(get_env PMA_PORT)/  (пользователь MYSQL_USER / MYSQL_PASSWORD)"
}

change_url() {
  local new=${1:?Укажите новый адрес: ./setup.sh url http://1.2.3.4:18081}
  new=${new%/}
  local old
  old=$(docker compose run --rm cli wp eval 'global $wpdb; echo $wpdb->get_var("SELECT option_value FROM $wpdb->options WHERE option_name = '"'"'home'"'"'");' | tr -d '\r')
  set_env WP_URL "$new"
  docker compose up -d --wait
  if [ -n "$old" ] && [ "$old" != "$new" ]; then
    echo "Меняю $old → $new в базе"
    docker compose run --rm cli wp search-replace "$old" "$new" --all-tables --skip-columns=guid
  fi
  echo "Сайт: $new/"
}

case "${1:-up}" in
  up) up ;;
  url) change_url "${2:-}" ;;
  reset) docker compose down -v; up ;;
  down) docker compose stop ;;
  *) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
