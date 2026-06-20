#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=.env
OUTPUT_DIR=backups
RETENTION_DAYS=14

usage() {
  cat <<'USAGE'
Usage: scripts/backup.sh [--env-file .env] [--output-dir backups] [--retention-days 14]

Creates PostgreSQL and media backups for the deployed Swarm stack.
The env file is parsed as KEY=VALUE without source.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file) ENV_FILE="${2:?missing value for --env-file}"; shift 2 ;;
    --output-dir) OUTPUT_DIR="${2:?missing value for --output-dir}"; shift 2 ;;
    --retention-days) RETENTION_DAYS="${2:?missing value for --retention-days}"; shift 2 ;;
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

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

load_env_file "$ENV_FILE"

: "${STACK_NAME:=sge}"
: "${POSTGRES_DB:=sge}"
: "${POSTGRES_USER:=sge}"
: "${POSTGRES_VERSION:=16}"

mkdir -p "$OUTPUT_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${OUTPUT_DIR}/${STACK_NAME}-${timestamp}"
mkdir -p "$backup_dir"

DB_CONTAINER="$(docker ps --filter "name=${STACK_NAME}_db" --format '{{.ID}}' | head -n 1)"
if [ -z "$DB_CONTAINER" ]; then
  echo "Could not find running DB container for stack ${STACK_NAME}" >&2
  exit 1
fi

echo "Backing up PostgreSQL from $DB_CONTAINER"
docker exec "$DB_CONTAINER" pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format custom \
  --no-owner \
  --file "/tmp/${POSTGRES_DB}.dump"
docker cp "$DB_CONTAINER:/tmp/${POSTGRES_DB}.dump" "$backup_dir/db.dump"
docker exec "$DB_CONTAINER" rm -f "/tmp/${POSTGRES_DB}.dump"

MEDIA_VOLUME="${STACK_NAME}_media_data"
if docker volume inspect "$MEDIA_VOLUME" >/dev/null 2>&1; then
  echo "Backing up media volume $MEDIA_VOLUME"
  docker run --rm \
    -v "${MEDIA_VOLUME}:/media:ro" \
    -v "$(pwd)/${backup_dir}:/backup" \
    alpine:3.20 \
    tar -czf /backup/media.tar.gz -C /media .
else
  echo "Media volume not found: $MEDIA_VOLUME; skipping media backup"
fi

find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -print -exec rm -rf {} +

echo "Backup written to $backup_dir"
echo "Restore DB example: cat $backup_dir/db.dump | docker exec -i <db-container> pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists"
