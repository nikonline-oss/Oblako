# Образ для запуска mongo_db_script.py (PyMongo ставится один раз при сборке)
FROM python:3.12-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUNBUFFERED=1
WORKDIR /lab
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt
COPY mongo_db_script.py shell_demo.js ./
CMD ["python", "mongo_db_script.py"]
