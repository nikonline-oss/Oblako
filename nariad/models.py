from django.db import models
from django.core.validators import MinValueValidator
from organizations.models import Organization
from employees.models import Employee
from customers.models import Customer
from products.models import Product
from brigadiers.models import Brigadier 

class Nariad(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        verbose_name="Организация"
    )
    brigadier = models.ForeignKey(
        Brigadier,
        on_delete=models.PROTECT,
        verbose_name="Бригадир"
    )
    responsible = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Ответственный",
        related_name="nariad_responsible"
    )
    issued_man = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Задание выдал",
        related_name="nariad_issued_man"
    )
    received = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Задание принял",
        related_name="nariad_received"
    )
    rationer = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Нормировщик",
        related_name="nariad_rationer"
    )
    date_of_issue = models.DateField("Дата выдачи")
    evaluation = models.CharField("Оценка качества выполненных работ", max_length=300)
    
    class Meta:
        verbose_name = "Наряд на сдельную работу"
        verbose_name_plural = "Наряды на сдельную работу"
        ordering = ['-date_of_issue']

    def __str__(self):
        return f"Наряд №{self.id}"

class NariadItem(models.Model):
    nariad = models.ForeignKey(
        Nariad,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Наряд на сдельную работу"
    )
    date = models.DateField("Дата")
    describer = models.CharField("Описание работ", max_length=300)
    category = models.CharField("Разряд", max_length=100)
    unit_time = models.FloatField("Штучное время")
    end_time = models.FloatField("Подготовительно-заключительное время")
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1)]
    )
    price = models.IntegerField("Принято количество работ")
    fulfil_time = models.IntegerField("Отработал часов")
    fulfil_day = models.IntegerField("Отработал дней")

    class Meta:
        verbose_name = "Позиция наряда"
        verbose_name_plural = "Позиции нарядов"

class NariadItemFis(models.Model):
    nariad = models.ForeignKey(
        Nariad,
        on_delete=models.CASCADE,
        related_name='workers',
        verbose_name="Наряд на сдельную работу"
    )
    fio = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        verbose_name="Сотрудник",
        related_name="fio_worker"
    )
    category = models.CharField("Категория", max_length=100)
    razriad = models.CharField("Разряд работы", max_length=100)
    tabel_num = models.IntegerField("Табельный номер")
    worked_hour = models.IntegerField("Отработано часов")
    worked_day = models.IntegerField("Отработано дней")
    summa = models.IntegerField("Сумма")
    
    class Meta:
        verbose_name = "Позиция рабочих наряда"
        verbose_name_plural = "Позиции рабочих наряда"