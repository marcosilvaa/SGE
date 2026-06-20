#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=.env
SKIP_BUILD=false
IMAGE_TAG=latest

usage() {
  cat <<'USAGE'
Usage: scripts/deploy.sh [--env-file .env] [--skip-build] [--tag latest]

Runs production deploy from the VPS:
  1. safely parses KEY=VALUE env file without source
  2. validates Swarm, secrets, network, DEBUG=false, healthcheck hosts
  3. git pull --ff-only
  4. docker build + push unless --skip-build
  5. docker stack deploy --with-registry-auth
  6. force-rolls the app service
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file) ENV_FILE="${2:?missing value for --env-file}"; shift 2 ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    --tag) IMAGE_TAG="${2:?missing value for --tag}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

load_env_file() {
  local file="$1" line key value
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      echo "Invalid env line: $line" >&2
      exit 1
    fi
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "$key=$value"
  done < "$file"
}

require_var() {
  local name="$1" value="${!name:-}"
  if [ -z "$value" ]; then
    echo "Missing required variable: $name" >&2
    exit 1
  fi
  if [[ "$value" == *"<"* || "$value" == *">"* ]]; then
    echo "Variable $name still contains placeholder: $value" >&2
    exit 1
  fi
}

require_secret() {
  local name="$1"
  if ! docker secret inspect "$name" >/dev/null 2>&1; then
    echo "Missing Docker secret: $name" >&2
    echo "Create: printf '%s' '<value>' | docker secret create $name -" >&2
    exit 1
  fi
}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

load_env_file "$ENV_FILE"

for var in STACK_NAME DOMAIN REGISTRY ACME_EMAIL ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS TRAEFIK_DASHBOARD_AUTH POSTGRES_DB POSTGRES_USER; do
  require_var "$var"
done

if [ "${DEBUG:-${DJANGO_DEBUG:-}}" != "False" ] && [ "${DEBUG:-${DJANGO_DEBUG:-}}" != "false" ]; then
  echo "Production deploy requires DEBUG=false or DJANGO_DEBUG=false" >&2
  exit 1
fi

case ",$ALLOWED_HOSTS," in
  *,localhost,*) ;;
  *) echo "ALLOWED_HOSTS must include localhost for container healthcheck" >&2; exit 1 ;;
esac
case ",$ALLOWED_HOSTS," in
  *,127.0.0.1,*) ;;
  *) echo "ALLOWED_HOSTS must include 127.0.0.1 for container healthcheck" >&2; exit 1 ;;
esac

if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -qx active; then
  echo "Docker Swarm is not active. Run: docker swarm init --advertise-addr <VPS_PUBLIC_IP>" >&2
  exit 1
fi

if ! docker network inspect traefik_public >/dev/null 2>&1; then
  echo "Missing external overlay network: traefik_public" >&2
  echo "Create: docker network create --driver=overlay --attachable traefik_public" >&2
  exit 1
fi

require_secret CLOUDFLARE_DNS_API_TOKEN
require_secret DJANGO_SECRET_KEY
require_secret POSTGRES_PASSWORD

IMAGE="${REGISTRY}:${IMAGE_TAG}"
export IMAGE_TAG

printf 'Deploy target: stack=%s image=%s domain=%s\n' "$STACK_NAME" "$IMAGE" "$DOMAIN"

git pull --ff-only

if [ "$SKIP_BUILD" != true ]; then
  docker build --build-arg "PYTHON_VERSION=${PYTHON_VERSION:-3.14}" -t "$IMAGE" .
  docker push "$IMAGE"
fi

# docker-stack.yml uses REGISTRY + IMAGE_TAG for the app image.
docker stack deploy -c docker-stack.yml --with-registry-auth "$STACK_NAME"

docker service update --force "${STACK_NAME}_app"

echo "Deploy submitted. Useful checks:"
echo "  docker stack services $STACK_NAME"
echo "  docker stack ps $STACK_NAME"
echo "  docker service logs -f ${STACK_NAME}_app"
echo "  docker service logs -f ${STACK_NAME}_traefik"
