from django.db import models
from accounts.models import Account  # Импортируем модель Account, если связь нужна

class Organization(models.Model):
    name = models.CharField("Название", max_length=255)
    address = models.CharField("Адрес", max_length=255)
    account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT,
        verbose_name="Счёт",
        null=True,
        blank=True
    )
    chief = models.CharField("Руководитель", max_length=100)
    financial_chief = models.CharField("Главный бухгалтер", max_length=100)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"