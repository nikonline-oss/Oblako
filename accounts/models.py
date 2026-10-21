from django.db import models

class Account(models.Model):
    account = models.CharField("Номер счёта", max_length=100)
    bank_name = models.CharField("Банк", max_length=200)
    bank_identity_number = models.CharField("БИК", max_length=50)

    def __str__(self):
        return f"{self.account} ({self.bank_name})"