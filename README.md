# Backup Hub

Backup Hub is a small FastAPI application for scheduled, encrypted backups with a clean web dashboard for listing and downloading backup archives.

![img.png](static/img/Screenshot.png)

## Features

- Scheduled backup jobs with Docker and `supercronic`
- AES-encrypted ZIP archives
- Password-based web login
- TOTP verification before every download
- Backup retention with automatic deletion of the oldest archive
- Temporary workspace cleanup before and after every backup run
- Step-by-step logs for backup phases, database dump phases, archive creation, cleanup, retention, and failures
- Directory backups from mounted volumes or mounted disks
- Database backups for PostgreSQL, MySQL/MariaDB, and MongoDB

## Important Paths

```text
fs/tmp       Temporary backup workspace
fs/backups   Encrypted backup archives
backup_providers/   Database-specific backup implementations
tasks/backup.py  Scheduled backup entrypoint
```

## Archive Layout

Each backup archive contains one root directory named after the backup timestamp:

```text
BACKUP-2025-01-01-12-12:00/disks/data1/f
BACKUP-2025-01-01-12-12:00/disks/data2/f
BACKUP-2025-01-01-12-12:00/databases/postgres/host_5432/db1.dump
BACKUP-2025-01-01-12-12:00/databases/mysql/host_3306/db1.sql
BACKUP-2025-01-01-12-12:00/databases/mongodb/mongo_uri/db1
```

Final archive files are saved in `fs/backups`:

```text
BACKUP-2025-01-01-12-12:00.zip
```

## Environment

Core settings:

```env
DEBUG=NO
PORT=8989
BASE_URL=http://localhost:8989
CORS_ALLOWEDS=http://localhost:8989,http://127.0.0.1:8989

BACKUP_HUB_CRON=0 3 * * *
BACKUP_HUB_MAX_BACKUPS=5
BACKUP_HUB_AES_ZIP_KEY=change-me-to-a-long-secret
BACKUP_HUB_DIRECTORIES=/data1/f,/data2/f

BACKUP_HUB_USERNAME=admin
BACKUP_HUB_PASSWORD=change-me
BACKUP_HUB_TOTP_SECRET=JBSWY3DPEHPK3PXP
BACKUP_HUB_SESSION_SECRET=change-me
BACKUP_HUB_SESSION_COOKIE=backup_hub_session
BACKUP_HUB_COOKIE_SECURE=YES
BACKUP_HUB_SESSION_TTL_SECONDS=28800
```

PostgreSQL:

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASES=
```

If `POSTGRES_DATABASES` is empty, Backup Hub discovers all non-template databases on the server.

MySQL/MariaDB:

```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASES=
```

If `MYSQL_DATABASES` is empty, Backup Hub discovers all user databases and skips system databases.

MongoDB:

```env
MONGO_URI=mongodb://admin:password@mongo:27017/?authSource=admin&authMechanism=SCRAM-SHA-256
MONGO_DATABASES=db1,db2
```

MongoDB only uses `MONGO_URI` and `MONGO_DATABASES`. Host, port, username, and password are expected to be part of the URI when needed.

For authenticated MongoDB connections, include `authSource` in the URI. If your MongoDB user is created in the `admin` database, use `authSource=admin`. It is also recommended to set the authentication mechanism explicitly, usually `authMechanism=SCRAM-SHA-256`.

When `MONGO_DATABASES` is set, do not put a database name in the URI path. `mongodump` receives the target database through `--db`, and it fails if the URI path points to a different database.

Correct:

```env
MONGO_URI=mongodb://admin:password@mongo:27017/?authSource=admin&authMechanism=SCRAM-SHA-256
MONGO_DATABASES=braintest
```

Wrong:

```env
MONGO_URI=mongodb://admin:password@mongo:27017/admin?authSource=admin&authMechanism=SCRAM-SHA-256
MONGO_DATABASES=braintest
```

## Docker

Build:

```bash
docker build -t backup-hub .
```

Run:

```bash
docker run --env-file .env -p 8989:80 \
  -v backup-hub-data:/app/fs \
  -v /data1/f:/data1/f:ro \
  -v /data2/f:/data2/f:ro \
  backup-hub
```

You can add directories as Docker volumes, bind mounts, or mounted disks. The path inside the container must be listed in `BACKUP_HUB_DIRECTORIES`.

## Manual Backup

```bash
python -m tasks.backup
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8989
```

Run tests:

```bash
python -m unittest tests
```
