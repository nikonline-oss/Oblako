from django.apps import AppConfig


class ActivityLogConfig(AppConfig):
    name = 'activity_log'
    verbose_name = 'Журнал действий (MongoDB)'

    def ready(self):
        from . import signals  # noqa: F401 — подключаем обработчики сигналов
