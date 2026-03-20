#!/usr/bin/env python3
"""
Valida SQLite antes de migrate / Gunicorn (logs em tempo real no Docker).
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
    log(' Fase 3: Verificacao SQLite')
    log('================================================================')

    try:
        import django

        django.setup()
    except Exception as e:
        log(f'ERRO: Falha ao carregar Django/settings: {e}')
        return 1

    from django.conf import settings
    from django.db import connections

    db_path = settings.DATABASES['default'].get('NAME', '')
    log(f'Ficheiro: {db_path}')
    parent = os.path.dirname(str(db_path))
    if parent and not os.path.isdir(parent):
        log(f'ERRO: Pasta nao existe: {parent}')
        log('       Bind mount no EasyPanel: /app/media')
        return 1
    try:
        conn = connections['default']
        conn.ensure_connection()
        with conn.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
    except Exception as e:
        log(f'ERRO: Nao foi possivel abrir/criar SQLite: {e}')
        log('       Verifique permissoes de escrita no volume.')
        return 1

    log('OK: SQLite acessivel.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
