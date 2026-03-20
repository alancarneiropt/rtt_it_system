#!/usr/bin/env bash
# Entrypoint produção: logs em tempo real (stdout/stderr) + verificação ordenada da BD.
set -eo pipefail

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] [RTT-IT] $*"; }

log "================================================================"
log " Arranque RTT-IT (producao) | verificacao pos-deploy"
log "================================================================"

if [[ "${DJANGO_PRODUCTION:-0}" != "1" ]]; then
  log "ERRO: DJANGO_PRODUCTION deve ser 1 nesta imagem."
  exit 1
fi
log "OK: DJANGO_PRODUCTION=1"

# --- Fase 1: resolver DB_* a partir de DATABASE_URL / POSTGRES_* / PG* ---
log "Fase 1/7: Resolver variáveis da base de dados..."
# stdout → ficheiro (exports); stderr → logs em tempo real no painel
_EXPORT_FILE="$(mktemp)"
trap 'rm -f "${_EXPORT_FILE}"' EXIT
if ! python /app/scripts/resolve_database_env.py > "${_EXPORT_FILE}"; then
  log "ERRO: Não foi possível obter DB_HOST / DB_NAME / DB_USER / DB_PASSWORD."
  log "      Veja as mensagens acima (DATABASE_URL ou POSTGRES_* no EasyPanel)."
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "${_EXPORT_FILE}"
set +a

# --- Fase 2: obrigatórias ---
log "Fase 2/7: Validar variáveis obrigatórias da aplicação..."
set +u
_missing=()
for v in DB_HOST DB_NAME DB_USER DB_PASSWORD DJANGO_SECRET_KEY; do
  if [[ -z "${!v:-}" ]]; then
    _missing+=("$v")
  fi
done
set -u

if [[ ${#_missing[@]} -gt 0 ]]; then
  log "ERRO: Variáveis ainda em falta após resolução: ${_missing[*]}"
  exit 1
fi

if [[ "${DJANGO_SECRET_KEY}" == django-insecure-* ]]; then
  log "ERRO: DJANGO_SECRET_KEY não pode ser a chave de desenvolvimento."
  exit 1
fi

: "${DB_PORT:=5432}"
export DB_PORT

log "    DB_HOST=${DB_HOST}  DB_PORT=${DB_PORT}  DB_NAME=${DB_NAME}  DB_USER=${DB_USER}  DB_PASSWORD=********"

# --- Fase 3: PostgreSQL ---
log "Fase 3/7: Testar ligação ao PostgreSQL (antes de migrate)..."
if ! python /app/scripts/check_db.py; then
  log "ERRO: Base de dados inacessível — deploy abortado."
  exit 1
fi

# --- Fase 4: migrações ---
log "Fase 4/7: Executar migrate..."
python manage.py migrate --noinput
log "OK: migrate concluído."

# --- Fase 5: estáticos ---
log "Fase 5/7: collectstatic..."
python manage.py collectstatic --noinput --clear
log "OK: collectstatic concluído."

# --- Fase 6: check Django ---
log "Fase 6/7: django check (integridade da app)..."
if ! python manage.py check; then
  log "ERRO: manage.py check falhou."
  exit 1
fi
log "OK: django check passou."

# --- Fase 7: Gunicorn ---
log "Fase 7/7: Iniciar Gunicorn em 0.0.0.0:8009 (logs de acesso no stdout)..."
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
