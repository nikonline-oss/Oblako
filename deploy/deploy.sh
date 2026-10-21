#!/usr/bin/env bash
# Выкладка всего проекта на удалённый сервер по SSH (на сервере нужен Docker с compose).
#
#   ./deploy/deploy.sh user@host [опции]
#
# Опции:
#   --dir DIR    каталог на сервере (по умолчанию crm, относительно домашнего)
#   --swarm      дополнительно поднять Swarm-ферму ЛР3 (нужны --privileged контейнеры)
#
# Что делает: копирует проект, кладёт настройки (.env.server → .env на сервере),
# запускает там ./project.sh up (проверка портов, сборка, запуск, наполнение WordPress).
# Если порт на сервере занят — останавливается и показывает, какой.
#
# Переменные окружения:
#   SSH_PORT=2222               нестандартный порт SSH
#   SSH_OPTS="-i ~/.ssh/key"    дополнительные опции ssh
#   ENV_FILE=...                локальный файл настроек сервера (по умолчанию .env.server)
set -euo pipefail
cd "$(dirname "$0")/.."

usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

TARGET=""
DIR=crm
SWARM=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR=$2; shift 2 ;;
    --swarm) SWARM=1; shift ;;
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
  # За основу берётся .env сервера (в нём пароли, сгенерированные при первом запуске),
  # из .env.server подставляются только НЕПУСТЫЕ значения — так пароли не теряются
  echo "==> Переношу настройки из $ENV_FILE в ~/$DIR/.env (остальное в .env сервера сохраняется)"
  tr -d '\r' < "$ENV_FILE" | "${SSH[@]}" "cd '$DIR' && cat > .env.new && touch .env && awk '
      FILENAME == ARGV[1] {
        i = index(\$0, \"=\")
        if (i && \$0 !~ /^#/) { k = substr(\$0, 1, i - 1); val[k] = substr(\$0, i + 1); order[++n] = k }
        next }
      { i = index(\$0, \"=\"); k = substr(\$0, 1, i - 1)
        if (i && \$0 !~ /^#/) { seen[k] = 1; if (val[k] != \"\") { print k \"=\" val[k]; next } }
        print }
      END { for (j = 1; j <= n; j++) if (!(order[j] in seen)) print order[j] \"=\" val[order[j]] }
    ' .env.new .env > .env.merged && mv .env.merged .env && rm -f .env.new"
else
  echo "==> $ENV_FILE нет — на сервере используется его .env (или создаётся из .env.example)"
fi

# Если адрес сайта не задан — берём адрес сервера из user@host
HOST=${TARGET#*@}
"${SSH[@]}" "cd '$DIR' && touch .env && if ! grep -qE '^PUBLIC_HOST=.+' .env || grep -qE '^PUBLIC_HOST=localhost\$' .env; then
  sed -i '/^PUBLIC_HOST=/d' .env && echo 'PUBLIC_HOST=$HOST' >> .env && echo '==> PUBLIC_HOST=$HOST'; fi"

echo "==> Запускаю ./project.sh up на сервере"
"${SSH[@]}" "cd '$DIR' && bash project.sh up"

if [ "$SWARM" = 1 ]; then
  echo "==> Swarm-ферма ЛР3"
  "${SSH[@]}" "cd '$DIR' && bash project.sh swarm up"
fi
