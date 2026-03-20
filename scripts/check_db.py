#!/usr/bin/env python3
"""
Valida conexão ao PostgreSQL antes de migrate / Gunicorn.
Falha com código != 0 e mensagem clara se não conseguir conectar.
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RTT_IT_System.settings')


def main() -> int:
    try:
        import django

        django.setup()
    except Exception as e:
        print(f'ERRO: Falha ao carregar Django/settings: {e}', file=sys.stderr)
        return 1

    from django.conf import settings
    from django.db import connections

    if not getattr(settings, 'DJANGO_PRODUCTION', False):
        print('AVISO: DJANGO_PRODUCTION não está ativo; check_db assume PostgreSQL em produção.')
    engine = settings.DATABASES['default'].get('ENGINE', '')
    if 'postgresql' not in engine:
        print(
            'ERRO: Esperado ENGINE PostgreSQL em produção. '
            'Defina DJANGO_PRODUCTION=1 e DB_HOST, DB_NAME, DB_USER, DB_PASSWORD.',
            file=sys.stderr,
        )
        return 1

    try:
        conn = connections['default']
        conn.ensure_connection()
        with conn.cursor() as c:
            c.execute('SELECT 1')
            c.fetchone()
    except Exception as e:
        host = settings.DATABASES['default'].get('HOST', '?')
        port = settings.DATABASES['default'].get('PORT', '?')
        print(
            f'ERRO: Não foi possível conectar ao PostgreSQL em {host}:{port}. '
            f'Detalhe: {e}',
            file=sys.stderr,
        )
        return 1

    print('PostgreSQL: conexão verificada com sucesso.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
