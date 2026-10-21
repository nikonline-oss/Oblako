from django.db import models


class DropboxCredential(models.Model):
    """Подключённый аккаунт Dropbox (одна запись на всё приложение)."""
    refresh_token = models.TextField()
    account_name = models.CharField(max_length=255, blank=True)
    connected_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.account_name or 'Dropbox'
