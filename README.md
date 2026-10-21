# CRM — лабораторные работы по облачным технологиям

Django-CRM (наряды на сдельную работу, сотрудники, товары, доверенности…), на которой выполнены лабораторные работы 2–7.

| ЛР | Тема | Где в проекте |
|---|---|---|
| 2 | Docker | [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml) |
| 3 | Docker Swarm | [swarm/](swarm/) |
| 4 | Dropbox API | [cloud_storage/](cloud_storage/) — раздел «Dropbox» |
| 5 | PaaS (Render) | [render.yaml](render.yaml), [Procfile](Procfile) |
| 6 | MongoDB | [lab6_mongodb/](lab6_mongodb/), [activity_log/](activity_log/) — раздел «MongoDB» |
| 7 | WordPress | [lab7_wordpress/](lab7_wordpress/) |

## Запуск всего

Нужен Docker (на Windows — Docker Desktop и Git Bash).

```bash
./project.sh up
```

Команда создаст `.env` (пароли генерируются), проверит порты, соберёт и запустит всё и выведет адреса:

- CRM: http://localhost:8000/nariad/
- WordPress: http://localhost:8081/
- phpMyAdmin: http://localhost:8082/

Остальные команды — `./project.sh` без аргументов.

## Документация

- [LABS.md](LABS.md) — что и как показывать по каждой лабе.
- [DEPLOY.md](DEPLOY.md) — выкладка на удалённый сервер, порты, управление.
- Отчёты: [ЛР2](lab2_docker_report.md), [ЛР3](lab3_swarm_report.md), [ЛР4](lab4_dropbox_report.md), [ЛР5](lab5_render_report.md), [ЛР6](lab6_mongodb_report.md), [ЛР7](lab7_wordpress_report.md).
