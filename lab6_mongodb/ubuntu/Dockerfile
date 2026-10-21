# Установка MongoDB 4.4 на Ubuntu 20.04 — шаги 1–2 методички ЛР6
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Шаг 1: ключ GPG, репозиторий MongoDB 4.4 для focal, установка mongodb-org
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
 && curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | apt-key add - \
 && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" \
      > /etc/apt/sources.list.d/mongodb-org-4.4.list \
 && apt-get update \
 && apt-get install -y mongodb-org \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /data/db

EXPOSE 27017

# Шаг 2: в контейнере нет systemd, поэтому вместо `systemctl start mongod`
# mongod запускается напрямую (как в /lib/systemd/system/mongod.service),
# но слушает все интерфейсы контейнера, чтобы к нему можно было подключиться
CMD ["mongod", "--bind_ip_all", "--dbpath", "/data/db"]
