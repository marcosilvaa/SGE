# PRD — Production Deploy Template for SGE Django on Docker Swarm

## 1. Overview and objective

This PRD specifies a production deployment template for the existing SGE Django project. The target is a repeatable VPS deployment architecture using Docker, Docker Compose for local/dev execution, Docker Swarm for production, Traefik as reverse proxy/load balancer, Cloudflare DNS-01 for wildcard TLS, PostgreSQL for production data, safe healthchecks, safe migrations, backups, and operational scripts.

This document is intentionally a planning artifact only. It does not implement Docker, settings, entrypoints, scripts, or application code yet.

Environment placeholders:

- Domain: `<DOMAIN>`
- Registry: `<REGISTRY>`, recommended default `ghcr.io/marcosilvaa/sge`
- Swarm stack name: `<STACK_NAME>`, recommended default `sge`
- Cloudflare DNS API Docker secret: `CLOUDFLARE_DNS_API_TOKEN`
- Reference stack inspected: `/home/scsi/scsi_v1/docker-stack.yml`

Non-negotiable constraints:

- Do not break existing SGE behavior.
- Do not commit secrets.
- Keep changes idempotent.
- Keep project coding style.
- Use environment-specific placeholders where real values belong.
- Add conditional components only when SGE actually needs them.

---

## 2. Current project diagnosis

### 2.1 Repository and state

Repository root:

```text
/home/sge/SGE
```

Django entrypoints:

```text
/home/sge/SGE/manage.py
/home/sge/SGE/app/settings.py
/home/sge/SGE/app/urls.py
/home/sge/SGE/app/wsgi.py
/home/sge/SGE/app/asgi.py
```

Current Git status before PRD creation:

```text
 M db.sqlite3
```

Important: `db.sqlite3` was already modified before this PRD work. Do not overwrite it during deploy-template implementation.

### 2.2 Python, Django, and relevant libraries

Python version files and runtime:

```text
.python-version: 3.14
.venv Python: Python 3.14.6
```

Django version:

```text
Django 6.0
```

Runtime dependencies from `requirements.txt`:

```text
asgiref==3.11.0
django==6.0
django-restframework==0.0.1
djangorestframework==3.16.1
djangorestframework-simplejwt==5.5.1
pyjwt==2.10.1
sqlparse==0.5.4
```

Relevant `pyproject.toml` facts:

```toml
requires-python = ">=3.14"
```

It also includes `flake8` and `pylint` in runtime dependencies. These should move to development-only dependencies later, but that is not part of the first deploy PRD implementation unless needed.

Findings:

- `django-restframework==0.0.1` appears suspicious/unnecessary. The canonical package is `djangorestframework`.
- Production deploy currently lacks `gunicorn`, PostgreSQL driver (`psycopg` or `psycopg-binary`), `django-environ` or equivalent env parser, and `whitenoise` if static files will be served by Django.
- Python 3.14 is newer than the SCSI reference stack (`python:3.13-slim`). The Dockerfile must explicitly handle Python 3.14 or the project must intentionally lower `requires-python` after testing.

### 2.3 Settings and configuration loading

Current `app/settings.py` behavior:

- Does not use `django-environ`.
- Does not use `os.environ` for project configuration.
- Does not read `.env`.
- `.env` exists but is empty.
- Values are hardcoded in settings.

Current important settings:

```python
SECRET_KEY = 'hardcoded value'
DEBUG = True
ALLOWED_HOSTS = []
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

Missing production settings:

- `CSRF_TRUSTED_ORIGINS`
- `SECURE_PROXY_SSL_HEADER`
- `SECURE_SSL_REDIRECT`
- `SECURE_REDIRECT_EXEMPT`
- HSTS settings
- secure cookies
- `STATIC_ROOT`
- `MEDIA_ROOT` / `MEDIA_URL`
- `DATABASE_URL`
- structured environment-based config

### 2.4 Security posture

`python manage.py check` passes with no issues.

`python manage.py check --deploy` reports 7 warnings:

```text
security.W004  SECURE_HSTS_SECONDS not set
security.W008  SECURE_SSL_REDIRECT not True
security.W009  SECRET_KEY weak/insecure
security.W012  SESSION_COOKIE_SECURE not True
security.W016  CSRF_COOKIE_SECURE not True
security.W018  DEBUG=True in deployment
security.W020  ALLOWED_HOSTS empty in deployment
```

Conclusion: the project works locally but is not production-ready.

### 2.5 Database

Current database:

```text
SQLite: /home/sge/SGE/db.sqlite3
```

Current settings:

```python
ENGINE = 'django.db.backends.sqlite3'
NAME = BASE_DIR / 'db.sqlite3'
```

Missing for production:

- PostgreSQL service.
- `DATABASE_URL` parsing.
- PostgreSQL driver.
- `wait_for_db` command.
- DB healthcheck.
- migration locking for multi-replica app deployment.

Production target: PostgreSQL 16 in Swarm with named volume.

### 2.6 Celery, RabbitMQ, Redis, cache, email, media, static

Current findings:

- No Celery usage found.
- No RabbitMQ usage found.
- No Redis usage found.
- No custom cache config found.
- No email config found.
- No `MEDIA_URL` / `MEDIA_ROOT` config found.
- Static config exists only for local development via `STATIC_URL` and `STATICFILES_DIRS`.
- No `STATIC_ROOT`.

Architecture decision for SGE:

- Do not include Celery, RabbitMQ, Redis, or Celery Beat in the first SGE deploy template.
- Keep these as optional future modules if SGE later adds async tasks, scheduled jobs, cache, or background email processing.
- Include PostgreSQL, Django web app, and Traefik.
- Include `media_data` and `static_data` volumes because they are safe production defaults for a Django app, even if current media usage is minimal.

### 2.7 Existing deploy artifacts

Current SGE has no deploy artifacts:

```text
Dockerfile                  missing
docker-compose.yml          missing
docker-stack.yml            missing
entrypoint.sh               missing
worker-entrypoint.sh        missing
scripts/deploy.sh           missing
scripts/backup.sh           missing
.github/workflows           missing
Procfile                    missing
gunicorn.conf.py            missing
healthcheck                 missing
production settings         missing
```

### 2.8 WSGI/ASGI and app server

Existing files:

```text
app/wsgi.py
app/asgi.py
```

Both use:

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
```

Production app server target:

```bash
gunicorn app.wsgi:application --bind 0.0.0.0:8000
```

No current `gunicorn` or `uvicorn` dependency exists.

### 2.9 URLs and healthcheck

Current `app/urls.py` includes:

```python
path('admin/', admin.site.urls)
path('login/', auth_views.LoginView.as_view(), name='login')
path('logout/', auth_views.LogoutView.as_view(), name='logout')
path('api/v1/', include('authentication.urls'))
path('', views.landing, name='landing')
path('dashboard/', views.home, name='home')
```

Missing:

```text
/health/
```

Target: lightweight unauthenticated `/health/` returning HTTP 200 without database access.

### 2.10 Particularities

- Template-based Django app plus JWT API.
- Uses SimpleJWT, but current settings appear to use non-standard keys:

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN": timedelta(days=1),
    "REFRESH_TOKEN": timedelta(days=7)
}
```

The usual SimpleJWT keys are `ACCESS_TOKEN_LIFETIME` and `REFRESH_TOKEN_LIFETIME`. This should be reviewed separately to avoid changing auth behavior accidentally.

- `.gitignore` ignores `.env`, `.venv`, and `media`, but ignores `db.sqlite`, not `db.sqlite3`. Because `db.sqlite3` exists and is modified, implementation should avoid touching it and may need a separate cleanup task later.

---

## 3. Reference stack analysis: SCSI

Reference file requested by Marco:

```text
/home/scsi/scsi_v1/docker-stack.yml
```

Key patterns to reuse for SGE:

### 3.1 Services in SCSI

SCSI stack contains:

```text
traefik
app
db
rabbitmq
redis
celery_worker
celery_beat
```

For SGE, use only:

```text
traefik
app
db
```

Do not include RabbitMQ, Redis, Celery Worker, or Celery Beat until SGE actually uses them.

### 3.2 Networks

SCSI pattern:

```yaml
traefik_public:
  external: true

scsi_v1_internal:
  driver: overlay
  internal: true
```

SGE target:

```yaml
traefik_public:
  external: true

sge_internal:
  driver: overlay
  internal: true
```

### 3.3 Volumes

SCSI pattern:

```yaml
pg_data
media_data
static_data
letsencrypt
redis_data
rabbitmq_data
```

SGE target:

```yaml
pg_data
media_data
static_data
letsencrypt
```

### 3.4 Cloudflare DNS-01 wildcard TLS

Reuse SCSI pattern:

```yaml
--certificatesresolvers.letsencrypt.acme.dnschallenge=true
--certificatesresolvers.letsencrypt.acme.dnschallenge.provider=cloudflare
CF_DNS_API_TOKEN_FILE=/run/secrets/CLOUDFLARE_DNS_API_TOKEN
```

Do not combine `tlschallenge` and `dnschallenge` on the same resolver.

Wildcard cert target:

```yaml
--entrypoints.websecure.http.tls.domains[0].main=${DOMAIN}
--entrypoints.websecure.http.tls.domains[0].sans=*.${DOMAIN}
```

### 3.5 Traefik healthcheck hostname

SCSI includes the critical label:

```yaml
traefik.http.services.scsi.loadbalancer.healthcheck.hostname=${DOMAIN}
```

SGE must include equivalent:

```yaml
traefik.http.services.sge.loadbalancer.healthcheck.hostname=${DOMAIN}
```

Reason: with restricted `ALLOWED_HOSTS`, Traefik may send the task IP as `Host`, causing Django `400 DisallowedHost` and marking backend unhealthy.

### 3.6 Entrypoints

SCSI app entrypoint:

- waits for DB with `wait_for_db`
- obtains PostgreSQL advisory lock
- runs migrations once safely
- runs `collectstatic`
- starts command

SGE target must reuse this pattern.

SCSI worker entrypoint:

- only waits for DB
- does not migrate
- does not collect static

SGE does not need worker entrypoint unless Celery is introduced later.

### 3.7 Deploy script

SCSI deploy script patterns to reuse:

- Parse `.env` safely without `source`.
- Validate Swarm active.
- Validate `CLOUDFLARE_DNS_API_TOKEN` secret exists.
- Validate `traefik_public` network exists.
- Validate `DEBUG=False` for production.
- Build and push image.
- Deploy with:

```bash
docker stack deploy -c docker-stack.yml --with-registry-auth <STACK_NAME>
```

- Force rollout for application services.

SGE deploy script should support:

```bash
./scripts/deploy.sh
./scripts/deploy.sh --skip-build
```

---

## 4. Gap analysis

### Essential gaps

- [ ] Environment-driven settings.
- [ ] Safe `.env.example`.
- [ ] Production-safe security settings.
- [ ] PostgreSQL support.
- [ ] Gunicorn production server.
- [ ] `/health/` endpoint.
- [ ] Dockerfile.
- [ ] `.dockerignore`.
- [ ] `entrypoint.sh` with `wait_for_db`, advisory-lock migrations, collectstatic.
- [ ] `wait_for_db` management command.
- [ ] Docker Compose for local/dev.
- [ ] Docker Stack for Swarm production.
- [ ] Traefik service with Cloudflare DNS-01 wildcard TLS.
- [ ] Docker secret usage for Cloudflare token.
- [ ] Healthchecks for app and DB.
- [ ] Restart policies, update/rollback configs, resource limits.
- [ ] `scripts/deploy.sh`.
- [ ] `scripts/backup.sh`.
- [ ] Deployment guide.
- [ ] Backup/restore procedure.

### Conditional gaps not applied now

- [ ] Celery worker.
- [ ] Celery beat.
- [ ] RabbitMQ.
- [ ] Redis.
- [ ] Redis cache.

Justification: no current SGE code references Celery/RabbitMQ/Redis/cache.

---

## 5. Architecture decisions for SGE

### 5.1 Service topology

Production Swarm services:

```text
<STACK_NAME>_traefik
<STACK_NAME>_app
<STACK_NAME>_db
```

Default names if placeholders are not overridden:

```text
sge_traefik
sge_app
sge_db
```

### 5.2 Images

App image:

```text
<REGISTRY>:latest
```

Recommended:

```text
ghcr.io/marcosilvaa/sge:latest
```

Production deploy command:

```bash
docker stack deploy -c docker-stack.yml --with-registry-auth <STACK_NAME>
```

### 5.3 Database

Use PostgreSQL 16.

Required environment variables:

```env
DATABASE_URL=postgres://sge:<POSTGRES_PASSWORD>@db:5432/sge
POSTGRES_DB=sge
POSTGRES_USER=sge
POSTGRES_PASSWORD=<secret>
```

Decision: keep DB password in `.env` initially because Docker Stack cannot interpolate Docker secret values directly into `DATABASE_URL` without extra entrypoint logic. Future hardening may move DB password to a Docker secret and compose `DATABASE_URL` at runtime from `_FILE` values.

### 5.4 Environment config

Use `.env` in project root for local/dev and separate `.env` on the VPS for production.

Docker services should receive variables via:

```yaml
env_file:
  - .env
```

Scripts must parse `.env` with a safe KEY=VALUE parser. Do not use:

```bash
source .env
. .env
```

Reason: values with `&`, `$`, `*`, `@`, spaces, quotes, and URLs can break shell parsing or execute unintended commands.

### 5.5 ALLOWED_HOSTS and CSRF

Production defaults:

```env
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://<DOMAIN>,https://*.<DOMAIN>
```

Rules:

- `ALLOWED_HOSTS` contains hostnames only, no scheme.
- Leading dot in `.<DOMAIN>` covers subdomains.
- `localhost` and `127.0.0.1` are mandatory because the container healthcheck hits `127.0.0.1`/`localhost`.
- `CSRF_TRUSTED_ORIGINS` must include scheme and can include wildcard.

### 5.6 TLS termination behind Traefik

Because TLS terminates at Traefik and Django receives internal HTTP, set:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

If enabling HTTPS redirect:

```python
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r'^health/$']
```

Reason: without proxy SSL header, Django may redirect forever behind Traefik.

### 5.7 Healthcheck

Add route:

```text
GET /health/ -> 200 OK
```

Requirements:

- no DB access
- no authentication
- tiny response body, e.g. `ok`
- works with `DEBUG=False`
- exempt from HTTPS redirect if needed

### 5.8 Static and media

Target settings:

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

Use volumes in Swarm:

```yaml
static_data:/app/staticfiles
media_data:/app/media
```

Static serving options:

1. Preferred simple option: add WhiteNoise and serve static from app.
2. Alternative: Traefik cannot serve files directly, so a separate nginx/static service would be needed.

Recommendation for SGE: add WhiteNoise in production path.

### 5.9 Zero-downtime updates

For app service:

```yaml
update_config:
  parallelism: 1
  delay: 15s
  order: start-first
  failure_action: rollback

rollback_config:
  parallelism: 1
  delay: 10s
  order: stop-first
```

Healthcheck must pass before Traefik routes traffic to the new task.

### 5.10 Resource controls

Start conservative for a single VPS:

```yaml
resources:
  limits:
    cpus: '1.00'
    memory: 768M
  reservations:
    cpus: '0.25'
    memory: 256M
```

Tune after observing real load.

### 5.11 Conditional async stack

Not implemented for SGE initially.

If SGE later adds Celery:

- add `celery_worker`
- add `celery_beat` only if scheduled tasks exist
- add RabbitMQ broker
- add Redis only if needed as cache/result backend
- add `worker-entrypoint.sh` that waits for DB but does not migrate or collect static

---

## 6. Technical specification: files to create or change

### 6.1 Create `.env.example`

Purpose: safe template for required environment variables.

Must include:

```env
DOMAIN=<DOMAIN>
STACK_NAME=sge
REGISTRY=ghcr.io/marcosilvaa/sge
DEBUG=False
SECRET_KEY=<generate-with-django>
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://<DOMAIN>,https://*.<DOMAIN>
DATABASE_URL=postgres://sge:<POSTGRES_PASSWORD>@db:5432/sge
POSTGRES_DB=sge
POSTGRES_USER=sge
POSTGRES_PASSWORD=<replace-me>
ACME_EMAIL=<email@example.com>
TRAEFIK_DASHBOARD_AUTH=<user:bcrypt-hash-with-dollar-doubled>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<smtp-host>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
DEFAULT_FROM_EMAIL=<noreply@domain>
```

Do not commit real `.env`.

### 6.2 Change `app/settings.py`

Add environment parsing with either:

- `django-environ`, or
- a small internal parser using `os.environ` and helper functions.

Recommended: `django-environ` for `DATABASE_URL` parsing.

Required behavior:

- `SECRET_KEY` from env.
- `DEBUG` boolean from env.
- `ALLOWED_HOSTS` comma-list from env.
- `CSRF_TRUSTED_ORIGINS` comma-list from env.
- `DATABASES` from `DATABASE_URL`, fallback to SQLite only when `DEBUG=True` or local dev.
- `SECURE_PROXY_SSL_HEADER` set in production.
- HSTS/cookie/nosniff settings when `DEBUG=False`.
- `SECURE_REDIRECT_EXEMPT` contains health path.
- `STATIC_ROOT`, `MEDIA_ROOT`, `MEDIA_URL` added.
- WhiteNoise added if chosen.

### 6.3 Create health endpoint

Options:

- Add a tiny view in `app/views.py`, or
- create `app/health.py`.

Required URL:

```python
path('health/', health_view, name='health')
```

Response:

```text
HTTP 200 ok
```

No DB query.

### 6.4 Create `wait_for_db` management command

Path suggestion:

```text
app/management/commands/wait_for_db.py
```

Requirements:

- Uses Django default DB connection.
- Retries until success or timeout.
- Supports `--timeout` argument.
- Logs retry progress.
- Exits non-zero on timeout.

### 6.5 Create `Dockerfile`

Base image must handle Python 3.14. Decision options:

Option A — keep Python 3.14:

```dockerfile
FROM python:3.14-slim
```

Use only if image is available/stable in deployment environment.

Option B — lower project Python support to 3.13 after verification:

```dockerfile
FROM python:3.13-slim
```

This requires testing Django 6.0 and project dependencies under Python 3.13 and updating `.python-version` / `pyproject.toml` only if safe.

Minimum Dockerfile pattern:

```dockerfile
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

### 6.6 Create `.dockerignore`

Must exclude:

```text
.git
.venv
__pycache__
*.pyc
.env
db.sqlite3
media
staticfiles
.pytest_cache
.mypy_cache
.coverage
```

### 6.7 Create `entrypoint.sh`

Required flow:

1. `python manage.py wait_for_db --timeout 90`
2. run migrations under PostgreSQL advisory lock
3. `python manage.py collectstatic --noinput --clear`
4. `exec "$@"`

Important:

- App entrypoint migrates and collects static.
- Future worker entrypoint must not migrate or collect static.

### 6.8 Create `docker-compose.yml`

Local/dev target:

- `app`
- `db`
- optional local Traefik profile or simple port mapping

Minimum local ports:

```yaml
app:
  ports:
    - "8000:8000"
```

Healthchecks:

- app `/health/`
- db `pg_isready`

### 6.9 Create `docker-stack.yml`

Production Swarm target adapted from SCSI:

Services:

- `traefik`
- `app`
- `db`

Networks:

- `traefik_public` external
- `sge_internal` internal overlay

Volumes:

- `pg_data`
- `media_data`
- `static_data`
- `letsencrypt`

Secret:

```yaml
CLOUDFLARE_DNS_API_TOKEN:
  external: true
```

App labels must include:

```yaml
traefik.enable=true
traefik.http.routers.sge.rule=Host(`${DOMAIN}`)
traefik.http.routers.sge.entrypoints=websecure
traefik.http.routers.sge.tls=true
traefik.http.routers.sge.tls.certresolver=letsencrypt
traefik.http.services.sge.loadbalancer.server.port=8000
traefik.http.services.sge.loadbalancer.healthcheck.path=/health/
traefik.http.services.sge.loadbalancer.healthcheck.hostname=${DOMAIN}
```

Traefik must include:

- HTTP to HTTPS redirect
- Cloudflare trusted IPs
- DNS-01 resolver only
- wildcard domain config
- dashboard protected by Basic Auth
- Cloudflare token via Docker secret file env convention

### 6.10 Create `scripts/deploy.sh`

Requirements:

- executable
- run on VPS from repo root
- parse `.env` safely
- validate Docker exists
- validate Swarm active
- validate `traefik_public` network exists
- validate `CLOUDFLARE_DNS_API_TOKEN` Docker secret exists
- validate `DEBUG=False`
- validate `ALLOWED_HOSTS` contains `localhost` and `127.0.0.1`
- validate `DOMAIN`, `REGISTRY`, `STACK_NAME`
- `git pull --ff-only`
- build image unless `--skip-build`
- push image unless `--skip-build`
- deploy with `docker stack deploy --with-registry-auth`
- force update `app` service
- print rollout status and useful commands

### 6.11 Create `scripts/backup.sh`

Requirements:

- executable
- parse `.env` safely
- create timestamped backup dir
- backup PostgreSQL via `pg_dump`
- backup media via `tar`
- rotate old backups
- document restore commands

Suggested backup path:

```text
/home/sge/backups/sge/YYYYmmdd-HHMMSS/
```

---

## 7. Implementation sprints

### S0 — Preparation and analysis

- [ ] File: `PRD.md` — Confirm this PRD is reviewed and values for `<DOMAIN>`, `<REGISTRY>`, and `<STACK_NAME>` are selected. Done when Marco approves or provides final values.
- [ ] File: Git working tree — Check `git status --short` and protect existing `db.sqlite3` modification. Done when implementation plan states whether to keep, ignore, or migrate local SQLite data.
- [ ] File: `requirements.txt`, `pyproject.toml`, `.python-version` — Decide Python Docker base (`python:3.14-slim` vs tested downgrade to 3.13). Done when build strategy is explicit and tested.

### S1 — Dockerfile, dependencies, entrypoint, wait_for_db

- [ ] File: `requirements.txt` — Add production dependencies: `gunicorn`, `django-environ`, PostgreSQL driver, and `whitenoise` if selected. Done when `pip install -r requirements.txt` succeeds.
- [ ] File: `Dockerfile` — Create production image build using selected Python version. Done when `docker build` succeeds.
- [ ] File: `.dockerignore` — Exclude secrets, venv, SQLite DB, caches, media, staticfiles. Done when build context does not include `.env` or `db.sqlite3`.
- [ ] File: `entrypoint.sh` — Add DB wait, advisory-lock migrations, collectstatic, and command exec. Done when script is executable and shellcheck-style review passes.
- [ ] File: `app/management/commands/wait_for_db.py` — Add timeout-based DB readiness command. Done when command succeeds against running DB and fails cleanly when DB is unavailable.

### S2 — Settings and environment

- [ ] File: `app/settings.py` — Add env-driven `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`. Done when local and production envs parse correctly.
- [ ] File: `app/settings.py` — Add `DATABASE_URL` support with SQLite fallback only for local/dev. Done when app connects to PostgreSQL in Docker.
- [ ] File: `app/settings.py` — Add `SECURE_PROXY_SSL_HEADER`, HTTPS redirect, redirect exemption for `/health/`, HSTS, secure cookies, nosniff. Done when `manage.py check --deploy` warnings are intentionally resolved or documented.
- [ ] File: `app/settings.py` — Add `STATIC_ROOT`, `MEDIA_ROOT`, `MEDIA_URL`, and WhiteNoise if selected. Done when `collectstatic --noinput` succeeds.
- [ ] File: `.env.example` — Create safe template with all required variables and no secrets. Done when deploy script can validate it after copying to `.env`.

### S3 — Health endpoint

- [ ] File: `app/views.py` or `app/health.py` — Add lightweight health view with no DB access. Done when `curl http://localhost:8000/health/` returns HTTP 200.
- [ ] File: `app/urls.py` — Register `path('health/', ...)`. Done when route resolves with `DEBUG=False`.
- [ ] File: tests if present, or new smoke script — Add health endpoint verification. Done when automated check confirms 200.

### S4 — Local Docker Compose

- [ ] File: `docker-compose.yml` — Add `app` and `db` services with env file and healthchecks. Done when `docker compose up -d --build` starts successfully.
- [ ] File: `docker-compose.yml` — Add named volumes for Postgres, staticfiles, and media. Done when data persists after container restart.
- [ ] File: README or `PRD.md` — Document local run commands. Done when a new operator can run the app locally from commands only.

### S5 — Production Docker Stack

- [ ] File: `docker-stack.yml` — Add `app`, `db`, and `traefik` services adapted from SCSI. Done when `docker stack config` validates with env values.
- [ ] File: `docker-stack.yml` — Add `traefik_public` external network and `sge_internal` internal overlay network. Done when Swarm creates internal network and uses existing public network.
- [ ] File: `docker-stack.yml` — Add volumes `pg_data`, `media_data`, `static_data`, `letsencrypt`. Done when services mount correct paths.
- [ ] File: `docker-stack.yml` — Add app deploy policies: `restart_policy`, `resources`, `update_config`, `rollback_config`. Done when service spec shows start-first update and rollback.
- [ ] File: `docker-stack.yml` — Add app and DB healthchecks. Done when `docker service ps` shows healthy tasks.

### S6 — Traefik and Cloudflare DNS-01 wildcard TLS

- [ ] File: `docker-stack.yml` — Configure Traefik Swarm provider and `traefik_public` network. Done when Traefik discovers only labelled services.
- [ ] File: `docker-stack.yml` — Configure HTTP to HTTPS redirect. Done when HTTP requests redirect to HTTPS.
- [ ] File: `docker-stack.yml` — Configure Cloudflare DNS-01 resolver using only DNS challenge. Done when wildcard cert is issued.
- [ ] File: `docker-stack.yml` — Configure `CF_DNS_API_TOKEN_FILE=/run/secrets/CLOUDFLARE_DNS_API_TOKEN`. Done when token is not present in plaintext stack file.
- [ ] File: `docker-stack.yml` — Configure Cloudflare trusted forwarded header IP ranges. Done when app sees correct scheme/client metadata.
- [ ] File: `docker-stack.yml` — Configure dashboard at `traefik.<DOMAIN>` protected by Basic Auth. Done when unauthenticated dashboard requests are rejected.
- [ ] File: `docker-stack.yml` — Add `loadbalancer.healthcheck.hostname=${DOMAIN}`. Done when Traefik app healthcheck does not trigger Django `DisallowedHost`.

### S7 — Deploy and backup scripts

- [ ] File: `scripts/deploy.sh` — Implement safe `.env` parser and validations. Done when bad env fails early with clear message.
- [ ] File: `scripts/deploy.sh` — Implement build/push/deploy/rollout flow. Done when `./scripts/deploy.sh --skip-build` redeploys without build.
- [ ] File: `scripts/backup.sh` — Implement PostgreSQL and media backup with rotation. Done when backup files are created and old backups rotate.
- [ ] File: `scripts/backup.sh` or docs — Add restore procedure. Done when restore command is documented and tested on a non-production DB.

### S8 — Validation and hardening

- [ ] Command: `python manage.py check` — Done when no issues.
- [ ] Command: `python manage.py check --deploy` — Done when warnings are resolved or intentionally documented.
- [ ] Command: `docker compose up -d --build` — Done when app and db become healthy locally.
- [ ] Command: `docker stack deploy --with-registry-auth` on VPS — Done when app, db, and traefik converge.
- [ ] Command: HTTPS smoke test — Done when `https://<DOMAIN>/health/` returns 200 with valid cert.
- [ ] Command: Traefik logs — Done when wildcard cert issuance via DNS-01 is confirmed.
- [ ] Command: `docker service update --force <STACK_NAME>_app` — Done when zero-downtime rollout completes.
- [ ] Command: backup and restore drill — Done when a backup can be restored in a test database.

---

## 8. Deploy guide: VPS Ubuntu from zero

This guide assumes commands run as a sudo-capable non-root deploy user unless noted. Replace placeholders before running.

### 8.1 Provision the VPS user

Create a non-root user, for example `sge`:

```bash
adduser sge
usermod -aG sudo sge
usermod -aG docker sge
```

Create SSH access:

```bash
mkdir -p /home/sge/.ssh
chmod 700 /home/sge/.ssh
chown -R sge:sge /home/sge/.ssh
```

Add the public key to:

```bash
nano /home/sge/.ssh/authorized_keys
chmod 600 /home/sge/.ssh/authorized_keys
chown -R sge:sge /home/sge/.ssh
```

Optional passwordless sudo:

```bash
echo 'sge ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/sge-nopasswd > /dev/null
sudo chmod 440 /etc/sudoers.d/sge-nopasswd
```

### 8.2 Update OS and install base tools

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw htop unzip apache2-utils
```

`apache2-utils` provides `htpasswd` for Traefik dashboard Basic Auth.

### 8.3 Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw --force enable
sudo ufw status verbose
```

### 8.4 Install Docker Engine and Compose plugin

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

Verify:

```bash
docker version
docker compose version
```

### 8.5 Initialize Docker Swarm

Use the VPS public IP:

```bash
docker swarm init --advertise-addr <VPS_PUBLIC_IP>
```

If Swarm is already active, verify:

```bash
docker info --format '{{.Swarm.LocalNodeState}}'
```

Create external Traefik network:

```bash
docker network create --driver=overlay --attachable traefik_public
```

The internal backend network is created by `docker stack deploy` from `docker-stack.yml`.

### 8.6 Cloudflare DNS records

In Cloudflare DNS for `<DOMAIN>` create:

```text
A     <DOMAIN>      <VPS_PUBLIC_IP>   proxied or DNS-only per policy
A     *             <VPS_PUBLIC_IP>   proxied or DNS-only per policy
```

If IPv6 is used, also create AAAA records.

### 8.7 Create Cloudflare DNS API token

In Cloudflare dashboard:

1. Go to API Tokens.
2. Create custom token.
3. Permissions:
   - Zone > DNS > Edit
   - Zone > Zone > Read may be needed depending on UI/API behavior.
4. Zone Resources:
   - Include > Specific zone > `<DOMAIN>`
5. Copy token once.

Create Docker secret on the VPS:

```bash
printf '%s' '<CLOUDFLARE_TOKEN>' | docker secret create CLOUDFLARE_DNS_API_TOKEN -
```

Verify:

```bash
docker secret inspect CLOUDFLARE_DNS_API_TOKEN
```

Do not put the token in `.env`, shell history, Git, or the stack file.

### 8.8 Create Traefik dashboard Basic Auth hash

```bash
htpasswd -nbB admin '<STRONG_PASSWORD>'
```

Example output:

```text
admin:$2y$05$abc...
```

In `.env`, every `$` must become `$$` for Docker stack labels:

```env
TRAEFIK_DASHBOARD_AUTH=admin:$$2y$$05$$abc...
```

### 8.9 Clone project and create production `.env`

```bash
cd /home/sge
git clone <REPO_URL> SGE
cd /home/sge/SGE
cp .env.example .env
chmod 600 .env
nano .env
```

Production `.env` minimum:

```env
DOMAIN=<DOMAIN>
STACK_NAME=sge
REGISTRY=ghcr.io/marcosilvaa/sge
DEBUG=False
SECRET_KEY=<generate-a-strong-django-secret>
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://<DOMAIN>,https://*.<DOMAIN>
DATABASE_URL=postgres://sge:<POSTGRES_PASSWORD>@db:5432/sge
POSTGRES_DB=sge
POSTGRES_USER=sge
POSTGRES_PASSWORD=<POSTGRES_PASSWORD>
ACME_EMAIL=<email@example.com>
TRAEFIK_DASHBOARD_AUTH=<admin:hash-with-dollar-doubled>
```

Generate a Django secret key without using the project settings:

```bash
python3 - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

If Django is not installed on host, run it inside a Python venv or use the container after build.

### 8.10 Login to registry

For GitHub Container Registry:

```bash
echo '<GITHUB_TOKEN>' | docker login ghcr.io -u <GITHUB_USERNAME> --password-stdin
```

Token scopes usually need package read/write permissions.

### 8.11 First deploy

Preferred after scripts exist:

```bash
./scripts/deploy.sh
```

Manual equivalent:

```bash
set -a
grep -E '^(DOMAIN|STACK_NAME|REGISTRY)=' .env
set +a

docker build -t <REGISTRY>:latest .
docker push <REGISTRY>:latest
docker stack deploy -c docker-stack.yml --with-registry-auth <STACK_NAME>
```

Do not use `source .env` in real scripts. The manual snippet above is only illustrative; production scripts must parse `.env` safely.

### 8.12 Verify services

```bash
docker stack services <STACK_NAME>
docker stack ps <STACK_NAME>
docker service ls
```

Check app logs:

```bash
docker service logs -f <STACK_NAME>_app
```

Check Traefik logs:

```bash
docker service logs -f <STACK_NAME>_traefik
```

Check DB health:

```bash
docker service ps <STACK_NAME>_db
```

### 8.13 Verify wildcard certificate issuance

Watch Traefik logs:

```bash
docker service logs -f <STACK_NAME>_traefik | grep -iE 'acme|certificate|cloudflare|dns'
```

Expected behavior:

- Traefik uses Cloudflare DNS-01 challenge.
- Cert covers `<DOMAIN>` and `*.<DOMAIN>`.
- No TLS challenge is configured for the same resolver.

Test HTTPS:

```bash
curl -I https://<DOMAIN>/health/
curl -I https://traefik.<DOMAIN>/
```

### 8.14 Daily operations

Redeploy with rebuild:

```bash
./scripts/deploy.sh
```

Redeploy without rebuild:

```bash
./scripts/deploy.sh --skip-build
```

View services:

```bash
docker stack services <STACK_NAME>
docker stack ps <STACK_NAME>
```

View logs:

```bash
docker service logs -f <STACK_NAME>_app
docker service logs -f <STACK_NAME>_db
docker service logs -f <STACK_NAME>_traefik
```

Force app rollout:

```bash
docker service update --force <STACK_NAME>_app
```

Run Django command in app container:

```bash
APP_CONTAINER=$(docker ps --filter 'name=<STACK_NAME>_app' --format '{{.ID}}' | head -n1)
docker exec -it "$APP_CONTAINER" python manage.py check
```

Create superuser:

```bash
APP_CONTAINER=$(docker ps --filter 'name=<STACK_NAME>_app' --format '{{.ID}}' | head -n1)
docker exec -it "$APP_CONTAINER" python manage.py createsuperuser
```

Run migrations manually only when needed:

```bash
APP_CONTAINER=$(docker ps --filter 'name=<STACK_NAME>_app' --format '{{.ID}}' | head -n1)
docker exec -it "$APP_CONTAINER" python manage.py migrate --noinput
```

Prefer normal deploy path because entrypoint handles migrations with advisory lock.

### 8.15 Troubleshooting

#### DisallowedHost on container healthcheck

Symptom:

```text
Invalid HTTP_HOST header: 'localhost' or '127.0.0.1'
```

Fix `.env`:

```env
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
```

Redeploy:

```bash
./scripts/deploy.sh --skip-build
```

#### Traefik backend unhealthy with 400 from Go-http-client

Symptom:

```text
GET /health/ 400
User-Agent: Go-http-client
DisallowedHost for 10.0.x.x
```

Cause: Traefik sends internal task IP as `Host` during load balancer healthcheck.

Fix label in `docker-stack.yml`:

```yaml
traefik.http.services.sge.loadbalancer.healthcheck.hostname=${DOMAIN}
```

Redeploy stack.

#### HTTPS redirect loop

Symptom: browser or curl loops between HTTP/HTTPS.

Cause: Django does not know original request was HTTPS at Traefik.

Fix in settings:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Also ensure Traefik forwards `X-Forwarded-Proto`.

#### RabbitMQ ACCESS_REFUSED

SGE does not use RabbitMQ now. If added later:

- verify `RABBITMQ_DEFAULT_USER`
- verify `RABBITMQ_DEFAULT_PASS`
- verify Celery `CELERY_BROKER_URL`
- if RabbitMQ volume was created with old credentials, credentials may persist in volume; rotate carefully or recreate volume only after backup/confirmation.

#### Certificate not issued

Common causes:

- wrong Cloudflare token
- token missing Zone DNS Edit scope
- token restricted to wrong zone
- Docker secret missing
- wrong env var; Traefik expects `CF_DNS_API_TOKEN_FILE`
- using TLS challenge together with DNS challenge on same resolver
- DNS records not pointing to VPS

Checks:

```bash
docker secret inspect CLOUDFLARE_DNS_API_TOKEN
docker service logs -f <STACK_NAME>_traefik
```

#### `failed to resolve host 'db'` during startup

Usually transient while Swarm creates networks/services.

Required mitigations:

- DB service healthcheck.
- App `wait_for_db` command.
- App restart policy.

#### Table does not exist during startup

Cause: app served traffic before migrations completed, or multiple replicas raced migrations.

Required mitigations:

- entrypoint waits for DB
- advisory lock around migrations
- Traefik only routes to healthy app tasks

### 8.16 Backup

Run:

```bash
./scripts/backup.sh
```

Expected outputs:

```text
/home/sge/backups/sge/<timestamp>/db.dump
/home/sge/backups/sge/<timestamp>/media.tar.gz
```

Manual DB backup example:

```bash
DB_CONTAINER=$(docker ps --filter 'name=<STACK_NAME>_db' --format '{{.ID}}' | head -n1)
docker exec "$DB_CONTAINER" pg_dump -U sge -d sge -Fc > db.dump
```

Manual media backup example:

```bash
docker run --rm -v <STACK_NAME>_media_data:/media -v "$PWD":/backup alpine tar -czf /backup/media.tar.gz -C /media .
```

### 8.17 Restore

Stop app to avoid writes:

```bash
docker service scale <STACK_NAME>_app=0
```

Restore database:

```bash
DB_CONTAINER=$(docker ps --filter 'name=<STACK_NAME>_db' --format '{{.ID}}' | head -n1)
cat db.dump | docker exec -i "$DB_CONTAINER" pg_restore -U sge -d sge --clean --if-exists
```

Restore media:

```bash
docker run --rm -v <STACK_NAME>_media_data:/media -v "$PWD":/backup alpine sh -c 'rm -rf /media/* && tar -xzf /backup/media.tar.gz -C /media'
```

Restart app:

```bash
docker service scale <STACK_NAME>_app=2
```

### 8.18 Secret rotation

Rotate Cloudflare token:

```bash
printf '%s' '<NEW_CLOUDFLARE_TOKEN>' | docker secret create CLOUDFLARE_DNS_API_TOKEN_v2 -
```

Update `docker-stack.yml` temporarily to use the new secret name, deploy, verify cert renewal path, then remove old secret after no service uses it:

```bash
docker secret rm CLOUDFLARE_DNS_API_TOKEN
```

For DB password rotation, plan a maintenance window unless implementing dual-password/application rolling rotation support.

---

## 9. Risks and points of attention

- Python 3.14 image availability: SGE requires Python >=3.14. Confirm `python:3.14-slim` availability before implementation or intentionally test/support Python 3.13.
- SQLite to PostgreSQL migration: existing `db.sqlite3` may contain data. Decide whether production starts empty or imports existing data.
- `db.sqlite3` is currently modified and may be tracked. Avoid accidental overwrite or commit.
- Secrets: never commit `.env`, Cloudflare token, DB password, or dashboard password.
- Docker secrets and `.env`: Docker Stack cannot directly substitute secret file contents into arbitrary env vars. Keep design simple first, harden later if needed.
- Traefik wildcard TLS: DNS-01 only. Do not mix `tlschallenge` with `dnschallenge` on the same resolver.
- Healthcheck Host header: keep `loadbalancer.healthcheck.hostname=${DOMAIN}` or Traefik may mark healthy Django tasks unhealthy.
- `ALLOWED_HOSTS`: must include `localhost` and `127.0.0.1` for internal container healthcheck.
- HTTPS redirect loop: set `SECURE_PROXY_SSL_HEADER` because TLS terminates at Traefik.
- Swarm ignores `depends_on`: readiness must use healthchecks, restart policies, and `wait_for_db`.
- Multiple replicas: migrations must use PostgreSQL advisory lock.
- Static files: Gunicorn does not serve static by itself unless WhiteNoise is configured. Alternative requires separate static server.
- Volumes: deleting `pg_data` or `media_data` destroys production data. Back up before any volume operation.
- Registry auth: `docker stack deploy --with-registry-auth` is required for private images.
- Resource limits: too-low limits can cause false healthcheck failures under migration/collectstatic/load.
- Cloudflare trusted IP list: needs maintenance if Cloudflare changes ranges.
- Traefik dashboard: must be protected by Basic Auth and not exposed unauthenticated.

---

## 10. Summary plan

SGE is currently a local Django 6.0 / Python 3.14 project using SQLite and hardcoded settings. It has no Docker/deploy artifacts yet. The production deploy template should adapt the SCSI Swarm architecture but simplify it: use Traefik + Django app + PostgreSQL only. Do not add Celery/RabbitMQ/Redis now because SGE does not use them.

First implementation wave should create environment-driven settings, PostgreSQL support, health endpoint, Dockerfile, entrypoint with advisory-lock migrations, local Compose, production Swarm stack, and deploy/backup scripts. Then validate locally and on VPS with real Docker output before marking tasks complete.
