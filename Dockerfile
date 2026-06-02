# Base Image
FROM mirror-docker.runflare.com/library/python:3.12-slim

# Build Arguments
ARG MONGO_TOOLS_VERSION=100.17.0
ARG MONGO_TOOLS_URL=https://iamshakeri.ir/fs/mongodb-database-tools-debian12-x86_64-100.17.0.tgz

# Runtime Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://mirror-pypi.runflare.com/simple \
    PORT=80 \
    BACKUP_HUB_CRON="0 3 * * *" \
    TZ=Asia/Tehran \
    SUPERCRONIC_URL=https://iamshakeri.ir/fs/supercronic-linux-amd64-0.2.39 \
    SUPERCRONIC_SHA1SUM=c98bbf82c5f648aaac8708c182cc83046fe48423 \
    SUPERCRONIC=supercronic-linux-amd64-0.2.39 \
    MONGO_TOOLS_VERSION=${MONGO_TOOLS_VERSION} \
    MONGO_TOOLS_URL=${MONGO_TOOLS_URL}

WORKDIR /app

# Configure APT Mirrors
RUN sed -i 's/deb.debian.org/mirror-linux.runflare.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirror-linux.runflare.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/https/http/g' /etc/apt/sources.list.d/debian.sources

# Install System Dependencies
RUN apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends ca-certificates curl default-mysql-client postgresql-client tzdata unzip -o Acquire::Check-Valid-Until=false \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Supercronic
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Set Timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Install MongoDB Tools
RUN curl -fsSL "$MONGO_TOOLS_URL" -o /tmp/mongodb-database-tools.download \
    && if tar -tzf /tmp/mongodb-database-tools.download >/dev/null 2>&1; then mv /tmp/mongodb-database-tools.download /tmp/mongodb-database-tools.tgz; else unzip -p /tmp/mongodb-database-tools.download > /tmp/mongodb-database-tools.tgz; fi \
    && tar -xzf /tmp/mongodb-database-tools.tgz -C /tmp \
    && cp /tmp/mongodb-database-tools-debian12-x86_64-${MONGO_TOOLS_VERSION}/bin/* /usr/local/bin/ \
    && rm -rf /tmp/mongodb-database-tools*

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy Application
COPY . .

# Create Storage Directories
RUN mkdir -p /app/fs/tmp /app/fs/backups

# Expose Web Port
EXPOSE 80

# Start Cron And Web Server
CMD ["sh", "-c", "printf '%s python -m tasks.backup\\n' \"${BACKUP_HUB_CRON:-0 3 * * *}\" > /tmp/backup.cron && supercronic /tmp/backup.cron & uvicorn main:app --host 0.0.0.0 --port ${PORT:-80} --timeout-keep-alive ${BACKUP_HUB_SERVER_KEEP_ALIVE_SECONDS:-120}"]
