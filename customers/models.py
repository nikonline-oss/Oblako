from django.db import models

class Customer(models.Model):
    name = models.CharField("Название", max_length=255)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Контрагент"
        verbose_name_plural = "Контрагенты"