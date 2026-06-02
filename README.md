# Backup Hub

Backup Hub is a small FastAPI application for scheduled, encrypted backups with a clean web dashboard for listing and downloading backup archives.

![img.png](static/img/Screenshot.png)

## Features

- Scheduled backup jobs with Docker and `supercronic`
- AES-encrypted ZIP archives
- Password-based web login
- TOTP verification before every download
- Temporary JWT download links with a 10-minute lifetime
- Native-speed downloads through Nginx `X-Accel-Redirect` in Docker
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

Backup Hub reads the following application environment variables. Docker-only build/runtime variables such as mirror URLs, `SUPERCRONIC_*`, `MONGO_TOOLS_*`, and `UVICORN_PORT` are not part of the application config.

### Core App

```env
DEBUG=NO
PORT=8989
BASE_URL=http://localhost:8989
CORS_ALLOWEDS=http://localhost:8989,http://127.0.0.1:8989
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `DEBUG` | `NO` | Enables FastAPI debug/reload behavior when set to `YES`. Keep `NO` in production. |
| `PORT` | `8989` | App port for local Uvicorn runs. In Docker, Nginx listens on port `80`. |
| `BASE_URL` | `http://localhost:<PORT>` | Public base URL used to derive default CORS origins. |
| `CORS_ALLOWEDS` | derived from `BASE_URL` | Comma-separated allowed browser origins. |

### Backup Runtime

```env
BACKUP_HUB_CRON=0 3 * * *
BACKUP_HUB_MAX_BACKUPS=5
BACKUP_HUB_AES_ZIP_KEY=change-me-to-a-long-secret
BACKUP_HUB_DIRECTORIES=/data1/f,/data2/f
BACKUP_HUB_USE_NGINX_ACCEL=YES
BACKUP_HUB_STRICT_SECURITY=YES
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `BACKUP_HUB_CRON` | `0 3 * * *` | Supercronic schedule for automatic backup jobs. Default is every day at 03:00. |
| `BACKUP_HUB_MAX_BACKUPS` | `5` | Maximum number of archives to keep. When the limit is reached, the oldest archive is deleted before creating a new one. |
| `BACKUP_HUB_AES_ZIP_KEY` | empty | AES password for encrypted ZIP archives. Required for backup creation. |
| `BACKUP_HUB_DIRECTORIES` | empty | Comma-separated filesystem paths to include under `disks/` in the archive. Mount these paths into Docker as volumes or disks. |
| `BACKUP_HUB_USE_NGINX_ACCEL` | `NO` | Uses Nginx `X-Accel-Redirect` for faster protected downloads. Set to `YES` when running with the provided Docker/Nginx setup. |
| `BACKUP_HUB_STRICT_SECURITY` | `NO` | Rejects insecure default auth/TOTP/session settings at startup. Set to `YES` in production. |

### Web Auth

```env
BACKUP_HUB_USERNAME=admin
BACKUP_HUB_PASSWORD=change-me
BACKUP_HUB_TOTP_SECRET=JBSWY3DPEHPK3PXP
BACKUP_HUB_SESSION_SECRET=change-me
BACKUP_HUB_SESSION_COOKIE=backup_hub_session
BACKUP_HUB_COOKIE_SECURE=YES
BACKUP_HUB_SESSION_TTL_SECONDS=28800
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `BACKUP_HUB_USERNAME` | `admin` | Username for the web login form. |
| `BACKUP_HUB_PASSWORD` | `1234` | Password for the web login form. Must be changed in production. |
| `BACKUP_HUB_TOTP_SECRET` | demo secret | Base32 TOTP secret used before download links are generated. Must be changed in production. |
| `BACKUP_HUB_SESSION_SECRET` | demo secret | HMAC secret for signed web sessions and JWT download links. Must be long and private. |
| `BACKUP_HUB_SESSION_COOKIE` | `slv_session` | Cookie name for the signed session token. |
| `BACKUP_HUB_COOKIE_SECURE` | `NO` | Sets the session cookie `Secure` flag. Use `YES` behind HTTPS. |
| `BACKUP_HUB_SESSION_TTL_SECONDS` | `900` | Web session lifetime in seconds. |
| `BACKUP_HUB_LOGO_URL` | local default | Logo URL used on the login/dashboard UI. |
| `BACKUP_HUB_FAVICON_URL` | local default | Favicon URL used by the browser. |

### PostgreSQL

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DATABASES=
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `POSTGRES_HOST` | empty | PostgreSQL host. If empty, PostgreSQL backup is skipped. |
| `POSTGRES_PORT` | `5432` | PostgreSQL port. |
| `POSTGRES_USER` | empty | PostgreSQL username. |
| `POSTGRES_PASSWORD` | empty | PostgreSQL password. Passed through `PGPASSWORD`, not command arguments. |
| `POSTGRES_DATABASES` | empty | Comma-separated database list. If empty, Backup Hub discovers all non-template databases on the server. |

### MySQL/MariaDB

```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASES=
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `MYSQL_HOST` | empty | MySQL/MariaDB host. If empty, MySQL backup is skipped. |
| `MYSQL_PORT` | `3306` | MySQL/MariaDB port. |
| `MYSQL_USER` | empty | MySQL/MariaDB username. |
| `MYSQL_PASSWORD` | empty | MySQL/MariaDB password. |
| `MYSQL_DATABASES` | empty | Comma-separated database list. If empty, Backup Hub discovers user databases and skips system databases. |

### MongoDB

```env
MONGO_URI=mongodb://admin:password@mongo:27017/?authSource=admin&authMechanism=SCRAM-SHA-256
MONGO_DATABASES=db1,db2
```

| Variable | Default | What It Does |
| --- | --- | --- |
| `MONGO_URI` | empty | MongoDB connection URI. If empty, MongoDB backup is skipped. |
| `MONGO_DATABASES` | empty | Comma-separated MongoDB database list. Required when `MONGO_URI` is set. |

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
