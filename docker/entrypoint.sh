#!/usr/bin/env bash
# Entrypoint produção: SQLite (EasyPanel /app/media) OU PostgreSQL.
set -eo pipefail

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] [RTT-IT] $*"; }

_use_sqlite() {
  case "${DJANGO_USE_SQLITE:-0}" in
    1|true|True|yes|Yes) return 0 ;;
  esac
  return 1
}

log "================================================================"
log " Arranque RTT-IT (producao) | verificacao pos-deploy"
log "================================================================"

if [[ "${DJANGO_PRODUCTION:-0}" != "1" ]]; then
  log "ERRO: DJANGO_PRODUCTION deve ser 1 nesta imagem."
  exit 1
fi
log "OK: DJANGO_PRODUCTION=1"

if _use_sqlite; then
  # --- SQLite: volume EasyPanel host .../volumes/db -> /app/media ---
  export DJANGO_USE_SQLITE=1
  : "${SQLITE_PATH:=/app/media/db.sqlite3}"
  export SQLITE_PATH
  log "Fase 1/7: Modo SQLite (sem PostgreSQL)"
  log "    SQLITE_PATH=${SQLITE_PATH}"
  log "    MEDIA_ROOT=uploads dentro de /app/media (defeito: /app/media/uploads)"
  _parent="$(dirname "${SQLITE_PATH}")"
  if [[ ! -d "${_parent}" ]]; then
    log "ERRO: Pasta ${_parent} nao existe — configure o bind mount no EasyPanel:"
    log "       Host: .../volumes/db  ->  Container: /app/media"
    exit 1
  fi
  mkdir -p "${_parent}/uploads" 2>/dev/null || true
  log "OK: Volume montado em ${_parent}"
else
  # --- PostgreSQL: resolver DB_* ---
  log "Fase 1/7: Resolver variáveis PostgreSQL (DATABASE_URL / POSTGRES_* / DB_*)..."
  _EXPORT_FILE="$(mktemp)"
  trap 'rm -f "${_EXPORT_FILE}"' EXIT
  if ! python /app/scripts/resolve_database_env.py > "${_EXPORT_FILE}"; then
    log "ERRO: Nao foi possivel obter DB_HOST / DB_NAME / DB_USER / DB_PASSWORD."
    log "      OU defina DJANGO_USE_SQLITE=1 para usar SQLite em /app/media/db.sqlite3"
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "${_EXPORT_FILE}"
  set +a
fi

# --- Fase 2 ---
log "Fase 2/7: Validar variáveis obrigatórias..."
set +u
if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  log "ERRO: DJANGO_SECRET_KEY nao definida."
  exit 1
fi
if _use_sqlite; then
  :
else
  for v in DB_HOST DB_NAME DB_USER DB_PASSWORD; do
    if [[ -z "${!v:-}" ]]; then
      log "ERRO: ${v} nao definida (modo PostgreSQL)."
      exit 1
    fi
  done
fi
set -u

if [[ "${DJANGO_SECRET_KEY}" == django-insecure-* ]]; then
  log "ERRO: DJANGO_SECRET_KEY nao pode ser a chave de desenvolvimento."
  exit 1
fi

if ! _use_sqlite; then
  : "${DB_PORT:=5432}"
  export DB_PORT
  log "    DB_HOST=${DB_HOST}  DB_PORT=${DB_PORT}  DB_NAME=${DB_NAME}  DB_USER=${DB_USER}  DB_PASSWORD=********"
fi

# --- Fase 3 ---
log "Fase 3/7: Testar base de dados (antes de migrate)..."
if ! python /app/scripts/check_db.py; then
  log "ERRO: Base de dados inacessivel — deploy abortado."
  exit 1
fi

log "Fase 4/7: Executar migrate..."
python manage.py migrate --noinput
log "OK: migrate concluido."

log "Fase 5/7: collectstatic..."
python manage.py collectstatic --noinput --clear
log "OK: collectstatic concluido."

log "Fase 6/7: django check..."
if ! python manage.py check; then
  log "ERRO: manage.py check falhou."
  exit 1
fi
log "OK: django check passou."

log "Fase 7/7: Gunicorn 0.0.0.0:8009..."
log "================================================================"
exec gunicorn RTT_IT_System.wsgi:application \
  --bind 0.0.0.0:8009 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --enable-stdio-inheritance
