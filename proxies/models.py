from django.db import models
from django.core.validators import MinValueValidator
from organizations.models import Organization
from employees.models import Employee
from customers.models import Customer
from products.models import Product

class Proxy(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        verbose_name="Организация"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Сотрудник"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        verbose_name="Контрагент"
    )
    date_of_issue = models.DateField("Дата выдачи")
    is_valid_until = models.DateField("Действительна до")
    
    class Meta:
        verbose_name = "Доверенность"
        verbose_name_plural = "Доверенности"
        ordering = ['-date_of_issue']

    def __str__(self):
        return f"Доверенность №{self.id}"

class ProxyItem(models.Model):
    proxy = models.ForeignKey(
        Proxy,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Доверенность"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name="Товар"
    )
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1)]
    )
    
    class Meta:
        verbose_name = "Позиция доверенности"
        verbose_name_plural = "Позиции доверенности"