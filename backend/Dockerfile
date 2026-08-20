FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --default-timeout=600 --retries=5 -r requirements.txt \
    && pip install --no-cache-dir celery redis croniter

COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]