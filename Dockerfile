FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GUNICORN_CMD_ARGS="--bind 0.0.0.0:8000 --workers 3 --timeout 300"

WORKDIR /app

# Сначала только зависимости — этот слой кешируется между сборками
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh

# Внутри контейнера приложение всегда на 8000, наружу — порт WEB_PORT из .env
EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "crm.wsgi:application"]
