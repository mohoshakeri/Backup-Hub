FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=80 \
    BACKUP_HUB_CRON="0 3 * * *" \
    MONGO_TOOLS_VERSION=100.17.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl default-mysql-client postgresql-client \
    && curl -L https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic \
    && curl -L https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-${MONGO_TOOLS_VERSION}.tgz -o /tmp/mongodb-database-tools.tgz \
    && tar -xzf /tmp/mongodb-database-tools.tgz -C /tmp \
    && cp /tmp/mongodb-database-tools-debian12-x86_64-${MONGO_TOOLS_VERSION}/bin/* /usr/local/bin/ \
    && rm -rf /tmp/mongodb-database-tools* \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/fs/tmp /app/fs/backups

EXPOSE 80

CMD ["sh", "-c", "printf '%s python -m tasks.backup\\n' \"${BACKUP_HUB_CRON:-0 3 * * *}\" > /tmp/backup.cron && supercronic /tmp/backup.cron & uvicorn main:app --host 0.0.0.0 --port ${PORT:-80} --timeout-keep-alive ${BACKUP_HUB_SERVER_KEEP_ALIVE_SECONDS:-120}"]
