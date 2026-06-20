# SGE deployment guide — Docker Swarm, Traefik, PostgreSQL

This guide documents the production deploy template implemented for SGE. It uses Docker Compose for local validation and Docker Swarm on a single-node VPS that can later scale.

## 1. VPS provisioning

Run as root or a sudo-capable user:

```bash
adduser sge
usermod -aG sudo sge
usermod -aG docker sge
mkdir -p /home/sge/.ssh
nano /home/sge/.ssh/authorized_keys
chown -R sge:sge /home/sge/.ssh
chmod 700 /home/sge/.ssh
chmod 600 /home/sge/.ssh/authorized_keys
```

Install base packages and Docker:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw htop unzip apache2-utils
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

Firewall:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw --force enable
```

## 2. Swarm and networks

```bash
docker swarm init --advertise-addr <VPS_PUBLIC_IP>
docker network create --driver=overlay --attachable traefik_public
```

The stack creates the internal backend overlay network automatically.

## 3. Cloudflare DNS and token

Create DNS records in Cloudflare:

```text
A  <DOMAIN>  <VPS_PUBLIC_IP>
A  *         <VPS_PUBLIC_IP>
```

Create a Cloudflare API token with:

- Zone > DNS > Edit
- Zone > Zone > Read if required by Cloudflare UI/API
- Zone resource limited to the target domain

Create the Docker secret:

```bash
printf '%s' '<CLOUDFLARE_TOKEN>' | docker secret create CLOUDFLARE_DNS_API_TOKEN -
```

## 4. Application secrets

```bash
printf '%s' '<DJANGO_SECRET_KEY>' | docker secret create DJANGO_SECRET_KEY -
printf '%s' '<POSTGRES_PASSWORD>' | docker secret create POSTGRES_PASSWORD -
```

Generate the Traefik dashboard Basic Auth value:

```bash
htpasswd -nbB admin '<STRONG_PASSWORD>'
```

In `.env`, double every `$` as `$$`.

## 5. Production `.env`

```bash
cd /home/sge/SGE
cp .env.example .env
chmod 600 .env
nano .env
```

Required production shape:

```env
PYTHON_VERSION=3.14
REGISTRY=ghcr.io/marcosilvaa/sge
IMAGE_TAG=latest
STACK_NAME=sge
DOMAIN=<DOMAIN>
ACME_EMAIL=admin@<DOMAIN>
TRAEFIK_DASHBOARD_AUTH=admin:$$2y$$...
APP_REPLICAS=2

DEBUG=false
DJANGO_DEBUG=false
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://<DOMAIN>,https://*.<DOMAIN>
DJANGO_ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://<DOMAIN>,https://*.<DOMAIN>
DJANGO_USE_WHITENOISE=true

POSTGRES_VERSION=16
POSTGRES_DB=sge
POSTGRES_USER=sge
```

Keep real secrets in Docker secrets, not in Git.

## 6. Registry login

For GHCR:

```bash
echo '<GITHUB_TOKEN>' | docker login ghcr.io -u <GITHUB_USERNAME> --password-stdin
```

## 7. First deploy

```bash
./scripts/deploy.sh --env-file .env
```

Redeploy without rebuild:

```bash
./scripts/deploy.sh --env-file .env --skip-build
```

## 8. Verify

```bash
docker stack services sge
docker stack ps sge
docker service logs -f sge_app
docker service logs -f sge_traefik
curl -I https://<DOMAIN>/health/
```

Verify DNS-01 wildcard issuance in Traefik logs:

```bash
docker service logs -f sge_traefik | grep -iE 'acme|certificate|cloudflare|dns'
```

## 9. Operations

Logs:

```bash
docker service logs -f sge_app
docker service logs -f sge_db
docker service logs -f sge_traefik
```

Force rollout:

```bash
docker service update --force sge_app
```

Run Django command:

```bash
APP_CONTAINER=$(docker ps --filter 'name=sge_app' --format '{{.ID}}' | head -n1)
docker exec -it "$APP_CONTAINER" python manage.py check
```

Create superuser:

```bash
APP_CONTAINER=$(docker ps --filter 'name=sge_app' --format '{{.ID}}' | head -n1)
docker exec -it "$APP_CONTAINER" python manage.py createsuperuser
```

## 10. Troubleshooting

### Container healthcheck fails with DisallowedHost

Ensure:

```env
ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
DJANGO_ALLOWED_HOSTS=<DOMAIN>,.<DOMAIN>,localhost,127.0.0.1
```

### Traefik backend unhealthy with 400 Go-http-client

Keep this label in `docker-stack.yml`:

```yaml
traefik.http.services.sge.loadbalancer.healthcheck.hostname=${DOMAIN}
```

### HTTPS redirect loop

Ensure Django has:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### Certificate not issued

Check:

- Docker secret `CLOUDFLARE_DNS_API_TOKEN` exists.
- Token has Zone DNS Edit on the correct zone.
- Traefik uses DNS-01 only.
- DNS A/wildcard points to the VPS.

### Startup DB errors

Swarm ignores `depends_on`. The app uses `wait_for_db`, healthchecks, and restart policy. Early transient `db` resolution errors should self-heal.

## 11. Backup and restore

Backup:

```bash
./scripts/backup.sh --env-file .env --output-dir /home/sge/backups/sge
```

Restore DB example:

```bash
DB_CONTAINER=$(docker ps --filter 'name=sge_db' --format '{{.ID}}' | head -n1)
cat /home/sge/backups/sge/<backup>/db.dump | docker exec -i "$DB_CONTAINER" pg_restore -U sge -d sge --clean --if-exists
```

Restore media example:

```bash
docker run --rm -v sge_media_data:/media -v /home/sge/backups/sge/<backup>:/backup alpine:3.20 sh -c 'rm -rf /media/* && tar -xzf /backup/media.tar.gz -C /media'
```

## 12. Secret rotation

Create a new secret name, update the stack file to reference it, deploy, verify, then remove the old secret after no service uses it.

For database password rotation, use a maintenance window unless dual-password rotation is implemented.

## 13. Automatic deploy with GitHub Actions

The repository includes `.github/workflows/deploy.yml`.

On every push to `main`, GitHub Actions will:

1. build a multi-arch Docker image for `linux/amd64` and `linux/arm64`;
2. push it to `ghcr.io/marcosilvaa/sge` with tags `latest` and the commit SHA;
3. connect to the VPS over SSH;
4. run `./scripts/deploy.sh --env-file .env --skip-build --tag <commit-sha>`.

Required GitHub repository secrets:

```text
VPS_HOST          VPS public IP or DNS name
VPS_USER          usually sge
VPS_SSH_KEY       private key allowed to SSH into VPS_USER
VPS_PORT          optional; defaults to 22
VPS_DEPLOY_PATH   optional; defaults to /home/sge/SGE
GHCR_USERNAME     GitHub username, e.g. marcosilvaa
GHCR_TOKEN        GitHub PAT with read:packages for the VPS docker pull
```

The workflow uses the built-in `GITHUB_TOKEN` to push the image to GHCR. Make sure the repository has Actions permission to write packages:

```text
GitHub repo -> Settings -> Actions -> General -> Workflow permissions -> Read and write permissions
```

The VPS still needs its own deploy prerequisites: `.env`, Docker secrets, Swarm active, `traefik_public` network, and GitHub SSH access for `git pull`.
