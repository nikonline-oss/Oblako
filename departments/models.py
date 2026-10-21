from django.db import models

class Department(models.Model):
    name = models.CharField("Название", max_length=255)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"