#!/usr/bin/env python3
"""
Valida conexão ao PostgreSQL antes de migrate / Gunicorn.
Saída em stderr com flush imediato (logs em tempo real no Docker / EasyPanel).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RTT_IT_System.settings')


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'[{ts}] [RTT-IT check_db] {msg}', file=sys.stderr, flush=True)


def main() -> int:
    log('================================================================')
    log(' Fase 3: Verificacao da base de dados (Django + PostgreSQL)')
    log('================================================================')

    try:
        import django

        django.setup()
    except Exception as e:
        log(f'ERRO: Falha ao carregar Django/settings: {e}')
        return 1

    from django.conf import settings
    from django.db import connections

    if not getattr(settings, 'DJANGO_PRODUCTION', False):
        log('AVISO: DJANGO_PRODUCTION não está ativo.')

    engine = settings.DATABASES['default'].get('ENGINE', '')
    if 'postgresql' not in engine:
        log(
            'ERRO: ENGINE não é PostgreSQL. Em produção use DJANGO_PRODUCTION=1 e DB_* ou DATABASE_URL.'
        )
        return 1

    db = settings.DATABASES['default']
    host = db.get('HOST', '?')
    port = db.get('PORT', '?')
    name = db.get('NAME', '?')
    user = db.get('USER', '?')
    log(f'A ligar a {host}:{port} / base={name} / utilizador={user} ...')

    try:
        conn = connections['default']
        conn.ensure_connection()
        with conn.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
    except Exception as e:
        log(f'ERRO: Ligação falhou: {e}')
        log('       Confirme: serviço Postgres a correr, rede Docker, firewall e credenciais.')
        return 1

    log('OK: PostgreSQL respondeu — pode continuar (migrate / Gunicorn).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
