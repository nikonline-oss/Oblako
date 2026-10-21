"""Запись создания, изменения и удаления объектов CRM в журнал MongoDB."""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .mongo import enabled, log_event, snapshot

TRACKED_APPS = {
    'accounts', 'brigadiers', 'customers', 'departments', 'employees', 'nariad',
    'organizations', 'positions', 'products', 'proxies', 'units',
}


def _tracked(sender, raw=False):
    # raw — загрузка фикстур (loaddata): такие сохранения не логируем
    return enabled() and not raw and sender._meta.app_label in TRACKED_APPS


@receiver(pre_save)
def remember_old_state(sender, instance, raw=False, **kwargs):
    if not _tracked(sender, raw) or instance._state.adding or instance.pk is None:
        return
    old = sender._default_manager.filter(pk=instance.pk).first()
    instance._activity_old = snapshot(old) if old is not None else None


@receiver(post_save)
def log_save(sender, instance, created, raw=False, **kwargs):
    if not _tracked(sender, raw):
        return
    new = snapshot(instance)
    old = getattr(instance, '_activity_old', None)
    if created or old is None:
        log_event('create', instance, data=new)
        return
    changes = {field: {'old': old.get(field), 'new': value}
               for field, value in new.items() if old.get(field) != value}
    if changes:  # сохранение без изменений не засоряет журнал
        log_event('update', instance, changes=changes)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if not _tracked(sender):
        return
    log_event('delete', instance, data=snapshot(instance))
