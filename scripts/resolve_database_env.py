#!/usr/bin/env python3
"""
Resolve variáveis DB_* a partir de formatos comuns (EasyPanel / Docker / Postgres).
- Escreve logs em stderr (visíveis em tempo real nos logs do container).
- Escreve em stdout linhas `export VAR=...` seguras para `eval` no entrypoint.
"""
from __future__ import annotations

import os
import re
import shlex
import sys
from urllib.parse import unquote, urlparse


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _export(name: str, value: str) -> str:
    return f"export {name}={shlex.quote(value)}"


def _from_database_url(url: str) -> dict[str, str] | None:
    u = url.strip()
    if not u.startswith(("postgresql://", "postgres://")):
        return None
    parsed = urlparse(u)
    if not parsed.hostname:
        log("ERRO: DATABASE_URL sem hostname válido.")
        return None
    user = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    dbname = (parsed.path or "").lstrip("/")
    if not dbname:
        log("ERRO: DATABASE_URL sem nome da base (path).")
        return None
    port = str(parsed.port or 5432)
    return {
        "DB_HOST": parsed.hostname,
        "DB_PORT": port,
        "DB_NAME": dbname,
        "DB_USER": user,
        "DB_PASSWORD": password,
    }


def main() -> int:
    log("================================================================")
    log(" RTT-IT | Fase 1: Base de dados (resolucao de variaveis)")
    log("================================================================")

    need = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    current = {k: os.environ.get(k, "").strip() for k in need}
    if all(current.values()):
        log("OK: DB_HOST, DB_NAME, DB_USER e DB_PASSWORD já estão definidas.")
        if os.environ.get("DB_PORT", "").strip():
            log(f"    DB_PORT={os.environ.get('DB_PORT')}")
        else:
            log("    DB_PORT não definido — será usado 5432.")
        return 0

    missing = [k for k in need if not current[k]]
    log(f"Aviso: faltam variáveis explícitas: {', '.join(missing)}")

    # 1) DATABASE_URL
    durl = os.environ.get("DATABASE_URL", "").strip()
    if durl:
        log("A tentar extrair credenciais de DATABASE_URL...")
        got = _from_database_url(durl)
        if got:
            for k, v in got.items():
                if k == "DB_PASSWORD":
                    log(f"    {k}=******** (definido)")
                else:
                    log(f"    {k}={v}")
            print(_export("DB_HOST", got["DB_HOST"]))
            print(_export("DB_PORT", got["DB_PORT"]))
            print(_export("DB_NAME", got["DB_NAME"]))
            print(_export("DB_USER", got["DB_USER"]))
            print(_export("DB_PASSWORD", got["DB_PASSWORD"]))
            log("OK: DATABASE_URL convertida para DB_*.")
            return 0
        log("ERRO: DATABASE_URL inválida ou não é PostgreSQL.")
        return 1

    # 2) POSTGRES_* (comum em stacks Docker / templates)
    ph = os.environ.get("POSTGRES_HOST", "").strip()
    pdb = os.environ.get("POSTGRES_DB", "").strip()
    pu = os.environ.get("POSTGRES_USER", "").strip()
    pp = os.environ.get("POSTGRES_PASSWORD", "").strip()
    pport = os.environ.get("POSTGRES_PORT", "").strip() or "5432"
    if ph and pdb and pu and pp:
        log("A usar POSTGRES_HOST / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD...")
        print(_export("DB_HOST", ph))
        print(_export("DB_PORT", pport))
        print(_export("DB_NAME", pdb))
        print(_export("DB_USER", pu))
        print(_export("DB_PASSWORD", pp))
        log("OK: Variáveis POSTGRES_* mapeadas para DB_*.")
        return 0

    # 3) PG* (libpq)
    gh = os.environ.get("PGHOST", "").strip()
    gd = os.environ.get("PGDATABASE", "").strip()
    gu = os.environ.get("PGUSER", "").strip()
    gp = os.environ.get("PGPASSWORD", "").strip()
    gport = os.environ.get("PGPORT", "").strip() or "5432"
    if gh and gd and gu and gp:
        log("A usar PGHOST / PGDATABASE / PGUSER / PGPASSWORD...")
        print(_export("DB_HOST", gh))
        print(_export("DB_PORT", gport))
        print(_export("DB_NAME", gd))
        print(_export("DB_USER", gu))
        print(_export("DB_PASSWORD", gp))
        log("OK: Variáveis PG* mapeadas para DB_*.")
        return 0

    log("")
    log("ERRO: Não foi possível determinar a ligação ao PostgreSQL.")
    log("       Para SQLite no EasyPanel (bind mount -> /app/media), defina:")
    log("       DJANGO_USE_SQLITE=1   (e opcional SQLITE_PATH=/app/media/db.sqlite3)")
    log("       Ou para PostgreSQL, defina no serviço da APP:")
    log("       A) DB_HOST, DB_NAME, DB_USER, DB_PASSWORD  [e opcionalmente DB_PORT]")
    log("       B) DATABASE_URL=postgresql://USER:SENHA@HOST:5432/NOME_BD")
    log("       C) POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
    log("")
    log("       O DB_HOST é o hostname do serviço PostgreSQL na rede Docker,")
    log("       NÃO é um caminho de pasta no disco (ex.: /etc/easypanel/...).")
    log("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
