from django import template
from django.apps import apps
from django.core.exceptions import FieldDoesNotExist

register = template.Library()


@register.filter
def show_value(value):
    """Значение поля из документа журнала в читаемом виде."""
    if value is None or value == '':
        return '—'
    if isinstance(value, dict) and 'repr' in value:
        return f"{value['repr']} (#{value['id']})"
    if isinstance(value, bool):
        return 'да' if value else 'нет'
    return value


@register.filter
def field_label(name, model_label):
    """Человеческое название поля по имени модели 'app.Model'."""
    try:
        return apps.get_model(model_label)._meta.get_field(name).verbose_name
    except (LookupError, ValueError, FieldDoesNotExist):
        return name
