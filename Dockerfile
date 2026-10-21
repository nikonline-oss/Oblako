FROM python:3.12-slim

# PORT — порт gunicorn внутри контейнера (gunicorn сам читает $PORT, как на Heroku)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    GUNICORN_CMD_ARGS="--workers 3 --timeout 300"

WORKDIR /app

# Сначала только зависимости — этот слой кешируется между сборками
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "crm.wsgi:application"]
