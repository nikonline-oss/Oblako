from django.db import models

class Employee(models.Model):
    last_name = models.CharField("Фамилия", max_length=100)
    first_name = models.CharField("Имя", max_length=100)
    middle_name = models.CharField("Отчество", max_length=100, blank=True)
    post = models.CharField("Должность", max_length=200)
    passport_series = models.CharField("Серия паспорта", max_length=10)
    passport_number = models.CharField("Номер паспорта", max_length=20)
    passport_issued_by = models.CharField("Кем выдан", max_length=255)
    passport_date_of_issue = models.DateField("Дата выдачи")

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ['last_name']