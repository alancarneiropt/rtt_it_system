#!/usr/bin/env bash
set -euo pipefail

log() { echo "[entrypoint] $*"; }

if [[ "${DJANGO_PRODUCTION:-0}" != "1" ]]; then
  log "ERRO: DJANGO_PRODUCTION deve ser 1 nesta imagem (produção)."
  exit 1
fi

for v in DB_HOST DB_NAME DB_USER DB_PASSWORD DJANGO_SECRET_KEY; do
  if [[ -z "${!v:-}" ]]; then
    log "ERRO: Variável obrigatória $v não definida."
    exit 1
  fi
done

if [[ "${DJANGO_SECRET_KEY}" == django-insecure-* ]]; then
  log "ERRO: DJANGO_SECRET_KEY não pode ser a chave de desenvolvimento."
  exit 1
fi

: "${DB_PORT:=5432}"

log "A verificar PostgreSQL (${DB_HOST}:${DB_PORT})..."
if ! python /app/scripts/check_db.py; then
  log "Abortar: base de dados inacessível."
  exit 1
fi

log "A executar migrate..."
python manage.py migrate --noinput

log "A executar collectstatic..."
python manage.py collectstatic --noinput --clear

log "A iniciar Gunicorn em 0.0.0.0:8009..."
exec gunicorn RTT_IT_System.wsgi:application \
  --bind 0.0.0.0:8009 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --enable-stdio-inheritance
