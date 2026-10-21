import os

import dropbox

from .models import DropboxCredential


def app_key():
    return os.environ.get('DROPBOX_APP_KEY', '')


def env_configured():
    """Токен задан через переменные окружения — подключение из интерфейса не нужно."""
    return bool(os.environ.get('DROPBOX_ACCESS_TOKEN') or os.environ.get('DROPBOX_REFRESH_TOKEN'))


def get_client():
    """Клиент Dropbox или None, если аккаунт ещё не подключён."""
    access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
    if access_token:
        return dropbox.Dropbox(oauth2_access_token=access_token)

    refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
    if not refresh_token:
        credential = DropboxCredential.objects.first()
        refresh_token = credential.refresh_token if credential else None
    if not refresh_token:
        return None

    return dropbox.Dropbox(
        oauth2_refresh_token=refresh_token,
        app_key=app_key(),
        app_secret=os.environ.get('DROPBOX_APP_SECRET') or None,
    )
