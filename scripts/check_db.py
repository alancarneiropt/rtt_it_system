#!/usr/bin/env python3
"""
Valida a base de dados antes de migrate / Gunicorn (PostgreSQL ou SQLite).
Logs em stderr com flush (tempo real no EasyPanel).
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
    log(' Fase 3: Verificacao da base de dados')
    log('================================================================')

    try:
        import django

        django.setup()
    except Exception as e:
        log(f'ERRO: Falha ao carregar Django/settings: {e}')
        return 1

    from django.conf import settings
    from django.db import connections

    engine = settings.DATABASES['default'].get('ENGINE', '')

    if 'sqlite' in engine:
        db_path = settings.DATABASES['default'].get('NAME', '')
        log(f'Modo SQLite — ficheiro: {db_path}')
        parent = os.path.dirname(str(db_path))
        if parent and not os.path.isdir(parent):
            log(f'ERRO: Pasta da base de dados nao existe: {parent}')
            log('       Confirme o bind mount EasyPanel -> /app/media')
            return 1
        try:
            conn = connections['default']
            conn.ensure_connection()
            with conn.cursor() as c:
                c.execute('SELECT 1')
                c.fetchone()
        except Exception as e:
            log(f'ERRO: Nao foi possivel abrir/criar SQLite: {e}')
            log('       Verifique permissoes de escrita no volume montado.')
            return 1
        log('OK: SQLite acessivel — pode continuar (migrate / Gunicorn).')
        return 0

    if 'postgresql' in engine:
        if not getattr(settings, 'DJANGO_PRODUCTION', False):
            log('AVISO: DJANGO_PRODUCTION nao esta ativo.')
        db = settings.DATABASES['default']
        host = db.get('HOST', '?')
        port = db.get('PORT', '?')
        name = db.get('NAME', '?')
        user = db.get('USER', '?')
        log(f'Modo PostgreSQL — {host}:{port} / base={name} / utilizador={user}')
        try:
            conn = connections['default']
            conn.ensure_connection()
            with conn.cursor() as c:
                c.execute('SELECT 1')
                c.fetchone()
        except Exception as e:
            log(f'ERRO: Ligação PostgreSQL falhou: {e}')
            return 1
        log('OK: PostgreSQL respondeu.')
        return 0

    log(f'ERRO: ENGINE nao suportado: {engine}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
