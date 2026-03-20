#!/usr/bin/env bash
# Entrypoint produção: apenas SQLite (volume EasyPanel -> /app/media).
set -eo pipefail

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] [RTT-IT] $*"; }

log "================================================================"
log " Arranque RTT-IT (producao) | SQLite + verificacao"
log "================================================================"

if [[ "${DJANGO_PRODUCTION:-0}" != "1" ]]; then
  log "ERRO: DJANGO_PRODUCTION deve ser 1 nesta imagem."
  exit 1
fi

: "${SQLITE_PATH:=/app/media/db.sqlite3}"
export SQLITE_PATH

log "Fase 1/6: SQLite em volume persistente"
log "    SQLITE_PATH=${SQLITE_PATH}"
log "    (bind mount EasyPanel: host .../volumes/db -> /app/media)"

_parent="$(dirname "${SQLITE_PATH}")"
if [[ ! -d "${_parent}" ]]; then
  log "ERRO: Pasta ${_parent} nao existe."
  log "       Crie o bind mount: Container /app/media"
  exit 1
fi
mkdir -p "${_parent}/uploads" 2>/dev/null || true
log "OK: Volume em ${_parent} (uploads: ${_parent}/uploads)"

log "Fase 2/6: Variaveis obrigatorias..."
if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  log "ERRO: DJANGO_SECRET_KEY nao definida."
  exit 1
fi
if [[ "${DJANGO_SECRET_KEY}" == django-insecure-* ]]; then
  log "ERRO: DJANGO_SECRET_KEY nao pode ser a chave de desenvolvimento."
  exit 1
fi
log "OK: DJANGO_SECRET_KEY definida"

log "Fase 3/6: Testar SQLite (antes de migrate)..."
if ! python /app/scripts/check_db.py; then
  log "ERRO: SQLite inacessivel — deploy abortado."
  exit 1
fi

log "Fase 4/6: migrate..."
python manage.py migrate --noinput
log "OK: migrate concluido."

log "Fase 5/6: collectstatic..."
python manage.py collectstatic --noinput --clear
log "OK: collectstatic concluido."

log "Fase 6/6: django check..."
if ! python manage.py check; then
  log "ERRO: manage.py check falhou."
  exit 1
fi
log "OK: django check passou."

log "Gunicorn 0.0.0.0:8009..."
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
