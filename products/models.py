from django.db import models
from django.core.validators import MinValueValidator

class Product(models.Model):
    name = models.CharField("Название", max_length=255)
    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    unit = models.ForeignKey(
        'units.Unit',
        on_delete=models.PROTECT,
        verbose_name="Единица измерения",
        related_name='products'
    )
    
    def __str__(self):
        return f"{self.name} ({self.price} руб.)"

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']