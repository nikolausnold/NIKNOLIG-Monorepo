#!/usr/bin/env bash
# Staging deployment helper. Never touches production (/opt/nold/backend) and never prints secrets.
# Usage (from /opt/nold/staging/backend):
#   scripts/staging-deploy.sh init-secrets   create missing staging secret files (mode 600)
#   scripts/staging-deploy.sh preflight      validate paths, secrets, configuration and host ports
#   scripts/staging-deploy.sh backup         pg_dump of the staging database (if it is running)
#   scripts/staging-deploy.sh deploy         preflight, backup, build, migrate, start API on 127.0.0.1:8001
#   scripts/staging-deploy.sh verify         local and public health plus fail-closed checks
set -euo pipefail
umask 077

STAGING_ROOT=/opt/nold/staging/backend
PRODUCTION_ROOT=/opt/nold/backend
STAGING_HOST=staging-api.niknolig.com
SECRET_NAMES=(postgres_password health_password device_api_password device_token_secret)

cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ "$(pwd -P)" == "$STAGING_ROOT" ]] || { echo "Refusing: must run from $STAGING_ROOT" >&2; exit 1; }
ENV_FILE=staging.env
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE (copy staging.env.example)" >&2; exit 1; }
[[ "$(stat -c %a "$ENV_FILE")" =~ ^[46]00$ ]] || { echo "$ENV_FILE must be mode 600" >&2; exit 1; }

# Values are read as data, never sourced/executed.
get() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- || true; }
SECRETS_DIR="$(get STAGING_SECRETS_DIR)"
[[ -n "$SECRETS_DIR" ]] || { echo "STAGING_SECRETS_DIR is required" >&2; exit 1; }
SECRETS_DIR="$(realpath -m -- "$SECRETS_DIR")"
DB_NAME="$(get STAGING_DB_NAME)"; DB_NAME="${DB_NAME:-niknolig_staging}"
STAGING_DB_NAME="$DB_NAME"
AUTH_ISSUER="$(get AUTH_ISSUER)"
AUTH_AUDIENCE="$(get AUTH_AUDIENCE)"
AUTH_JWKS_URL="$(get AUTH_JWKS_URL)"
export STAGING_SECRETS_DIR="$SECRETS_DIR" STAGING_DB_NAME
export AUTH_ISSUER AUTH_AUDIENCE AUTH_JWKS_URL
dc() { env -u COMPOSE_PROJECT_NAME docker compose --project-name niknolig-staging --env-file "$ENV_FILE" -f compose.staging.yaml "$@"; }

init_secrets() {
  [[ -n "$SECRETS_DIR" && "$SECRETS_DIR" == /opt/nold/staging/* ]] || { echo "STAGING_SECRETS_DIR must be under /opt/nold/staging/" >&2; exit 1; }
  install -d -m 700 "$SECRETS_DIR"
  for name in "${SECRET_NAMES[@]}"; do
    [[ -s "$SECRETS_DIR/$name" ]] || { openssl rand -hex 32 > "$SECRETS_DIR/$name"; echo "created $name"; }
  done
}

preflight() {
  [[ "$SECRETS_DIR" == /opt/nold/staging/* ]] || { echo "STAGING_SECRETS_DIR must be under /opt/nold/staging/" >&2; exit 1; }
  [[ "$DB_NAME" =~ ^[a-z][a-z0-9_]{2,40}$ && "$DB_NAME" != niknolig_health ]] || { echo "Invalid or production database name" >&2; exit 1; }
  local seen=""
  for name in "${SECRET_NAMES[@]}"; do
    local file="$SECRETS_DIR/$name"
    [[ -s "$file" ]] || { echo "Missing or empty secret: $name" >&2; exit 1; }
    [[ "$(stat -c %a "$file")" == 600 ]] || { echo "Secret $name must be mode 600" >&2; exit 1; }
    [[ "$(wc -l < "$file")" -le 1 ]] || { echo "Secret $name must be single-line" >&2; exit 1; }
    local digest; digest="$(sha256sum "$file" | cut -d' ' -f1)"
    [[ "$seen" != *"$digest"* ]] || { echo "Staging secrets must all differ" >&2; exit 1; }
    seen+="$digest "
    # No staging secret may equal any file in a production secrets directory, when one is declared.
    if [[ -n "${PRODUCTION_SECRETS_DIR:-}" && -d "$PRODUCTION_SECRETS_DIR" ]]; then
      if find "$PRODUCTION_SECRETS_DIR" -maxdepth 1 -type f -exec sha256sum {} + | grep -q "$digest"; then
        echo "Staging secret $name matches a production secret" >&2; exit 1
      fi
    fi
  done
  local issuer jwks; issuer="$(get AUTH_ISSUER)"; jwks="$(get AUTH_JWKS_URL)"
  [[ "$issuer" =~ ^https://[a-z0-9]{10,40}\.supabase\.co/auth/v1$ && "$jwks" == "$issuer/.well-known/jwks.json" ]] \
    || { echo "AUTH_ISSUER/AUTH_JWKS_URL must be the Supabase staging project (not placeholders)" >&2; exit 1; }
  [[ -n "$(get AUTH_AUDIENCE)" ]] || { echo "AUTH_AUDIENCE missing" >&2; exit 1; }
  if [[ -n "${PRODUCTION_AUTH_ISSUER:-}" && "$issuer" == "$PRODUCTION_AUTH_ISSUER" ]]; then
    echo "Staging must use its own Supabase project, not the production issuer" >&2; exit 1
  fi
  dc config --quiet
  # Port 8001 must be free or already ours; production services are never stopped or modified here.
  if ss -ltn 'sport = :8001' | grep -q LISTEN && ! dc ps --status running api 2>/dev/null | grep -q api; then
    echo "Port 8001 is in use by another process" >&2; exit 1
  fi
  echo "Preflight passed. Production at $PRODUCTION_ROOT is untouched."
}

backup() {
  if dc ps --status running postgres 2>/dev/null | grep -q postgres; then
    install -d -m 700 /opt/nold/staging/backups
    local out; out="/opt/nold/staging/backups/${DB_NAME}-$(date -u +%Y%m%dT%H%M%SZ).sql"
    dc exec -T postgres pg_dump -U backend_migrator -d "$DB_NAME" --no-owner > "$out"
    [[ -s "$out" ]] || { rm -f "$out"; echo "Backup is empty" >&2; exit 1; }
    echo "Backup written: $out"
  else
    echo "No running staging database; nothing to back up."
  fi
}

verify() {
  local code
  curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8001/health/ready >/dev/null
  echo "local /health/ready ok"
  code="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 10 http://127.0.0.1:8001/v1/devices/me)"
  [[ "$code" == 401 ]] || { echo "Unauthenticated protected route returned $code (expected 401)" >&2; exit 1; }
  echo "unauthenticated protected route rejected ($code)"
  curl --fail --silent --show-error --proto '=https' --max-time 15 "https://$STAGING_HOST/health/ready" >/dev/null
  echo "public https://$STAGING_HOST/health/ready ok"
}

case "${1:-}" in
  init-secrets) init_secrets ;;
  preflight) preflight ;;
  backup) preflight; backup ;;
  deploy)
    preflight
    dc up -d --wait postgres
    backup
    dc build api
    dc run --rm migrate
    dc up -d --wait api
    echo "Deployed. Run: scripts/staging-deploy.sh verify"
    ;;
  verify) verify ;;
  *) sed -n 2,9p "$0"; exit 2 ;;
esac
