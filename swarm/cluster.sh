#!/usr/bin/env bash
# Локальная swarm-ферма из 4 узлов (docker-in-docker):
#   manager  — менеджер и "узел БД" (role=db)
#   worker1..3 — "веб-серверные узлы" (role=web)
# Использование: ./swarm/cluster.sh up | down | status
# Порты на хосте: SWARM_HTTP_PORT (сайт фермы, по умолчанию 80),
#                 REGISTRY_PORT (локальный registry, по умолчанию 5000).
# Берутся из окружения, иначе из .env. Остальные порты фермы (2377, 7946, 4789)
# живут только во внутренней сети swarm-lab и хост не занимают.
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."

NET=swarm-lab
WORKERS="worker1 worker2 worker3"
DIND=docker:27-dind
ON() { docker exec "$1" docker "${@:2}"; }

from_env() { [ -f .env ] && grep -E "^$1=" .env | cut -d= -f2- | tr -d '\r' || true; }
SWARM_HTTP_PORT=${SWARM_HTTP_PORT:-$(from_env SWARM_HTTP_PORT)}
SWARM_HTTP_PORT=${SWARM_HTTP_PORT:-80}
REGISTRY_PORT=${REGISTRY_PORT:-$(from_env REGISTRY_PORT)}
REGISTRY_PORT=${REGISTRY_PORT:-5000}

up() {
  docker network inspect $NET >/dev/null 2>&1 || docker network create $NET

  # Локальный registry — аналог DockerHub, из него узлы скачивают образ приложения
  docker run -d --name registry --network $NET -p "$REGISTRY_PORT":5000 registry:2

  docker run -d --privileged --name manager --hostname manager --network $NET \
    -e DOCKER_TLS_CERTDIR= -p "$SWARM_HTTP_PORT":80 $DIND --insecure-registry registry:5000
  for w in $WORKERS; do
    docker run -d --privileged --name $w --hostname $w --network $NET \
      -e DOCKER_TLS_CERTDIR= $DIND --insecure-registry registry:5000
  done

  for n in manager $WORKERS; do
    until ON $n info >/dev/null 2>&1; do sleep 1; done
  done

  ON manager swarm init --advertise-addr eth0
  TOKEN=$(ON manager swarm join-token -q worker)
  for w in $WORKERS; do ON $w swarm join --token "$TOKEN" manager:2377; done

  ON manager node update --label-add role=db manager
  for w in $WORKERS; do ON manager node update --label-add role=web $w; done

  # Хост пушит в registry по своему порту, узлы фермы тянут по внутреннему registry:5000
  docker build -t "localhost:$REGISTRY_PORT/crm-web:latest" .
  docker push "localhost:$REGISTRY_PORT/crm-web:latest"

  docker cp swarm/docker-stack.yml manager:/docker-stack.yml
  ON manager stack deploy -c /docker-stack.yml crm
  echo "Ферма запущена: http://localhost:$SWARM_HTTP_PORT/"
}

down() {
  docker rm -f manager $WORKERS registry 2>/dev/null || true
  docker network rm $NET 2>/dev/null || true
}

status() {
  ON manager node ls
  ON manager stack services crm
  ON manager service ps crm_db crm_web --filter desired-state=running
}

"${1:-status}"
