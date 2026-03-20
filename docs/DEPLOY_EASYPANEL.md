# Deploy RTT-IT no EasyPanel (Docker)

Este projeto corre em **produção** com:

- **Python 3.12** (imagem `python:3.12-slim-bookworm`)
- **Gunicorn** em `0.0.0.0:8009`
- **Base de dados:** **SQLite** em volume montado (`/app/media/db.sqlite3`) **ou** **PostgreSQL** externo
- **WhiteNoise** para ficheiros estáticos após `collectstatic`
- **Healthcheck**: `GET /health/`

## 1. Base de dados — SQLite (EasyPanel / bind mount)

1. No serviço **APP**, em **Montagens**, crie um **Bind Mount**:
   - **Caminho do host:** ex. `/etc/easypanel/projects/.../volumes/db`
   - **Caminho de montagem (container):** `/app/media`
2. Nas **variáveis de ambiente** da app:
   - `DJANGO_USE_SQLITE=1`
   - `SQLITE_PATH=/app/media/db.sqlite3` (opcional; é o valor por defeito)
3. O ficheiro `db.sqlite3` é criado/atualizado **dentro** dessa pasta no primeiro `migrate`.
4. **Uploads** (media) usam `/app/media/uploads` por defeito (subpasta, para não misturar com o ficheiro da BD).

## 2. Base de dados — PostgreSQL (externo)

1. No EasyPanel, crie uma instância **PostgreSQL** (ou use um servidor gerido).
2. Crie manualmente a **base de dados** e o **utilizador** com permissões sobre essa BD.
3. Anote: `host`, `porta` (geralmente `5432`), `database`, `user`, `password`.

O container da aplicação **não cria** a base de dados. Se a BD não existir ou as credenciais estiverem erradas, o **entrypoint falha** com mensagem explícita e o container não sobe.

## 3. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha. No EasyPanel, defina as mesmas variáveis no serviço da app.

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DJANGO_PRODUCTION` | Sim (Docker) | Deve ser `1` — a imagem já define por defeito. |
| `DJANGO_DEBUG` | Sim | `0` em produção. |
| `DJANGO_SECRET_KEY` | Sim | Chave secreta forte (não use a de desenvolvimento). |
| `ALLOWED_HOSTS` | Sim | Domínios/IP separados por vírgula (sem `*`). |
| `DJANGO_USE_SQLITE` | Para SQLite | `1` — usa ficheiro em `SQLITE_PATH` (não exige `DB_*`). |
| `SQLITE_PATH` | Não | Por defeito `/app/media/db.sqlite3`. |
| `DB_HOST` | Sim* | Só PostgreSQL: host do serviço (não é caminho de pasta). |
| `DB_PORT` | Não | PostgreSQL: por defeito `5432`. |
| `DB_NAME` | Sim* | PostgreSQL |
| `DB_USER` | Sim* | PostgreSQL |
| `DB_PASSWORD` | Sim* | PostgreSQL |

\* **PostgreSQL — alternativa:** `DATABASE_URL` ou `POSTGRES_*`; o entrypoint converte para `DB_*`.

| `CSRF_TRUSTED_ORIGINS` | Recomendado | URLs `https://...` separadas por vírgula. |
| `USE_X_FORWARDED_PROTO` | Recomendado | `1` se o proxy terminar HTTPS. |

## 4. Build e arranque (Docker local)

```bash
cp .env.example .env
# Edite .env com valores reais

docker compose build
docker compose up -d
```

A app escuta na porta **8009** do container; o `docker-compose.yml` mapeia `8009:8009`.

## 5. EasyPanel — App Docker

1. Crie um novo **App** do tipo Docker (build a partir do repositório ou imagem).
2. **Dockerfile**: na raiz do projeto (`Dockerfile`).
3. **Porta interna do container**: **8009** (Gunicorn).
4. No proxy reverso do EasyPanel, aponte para a porta publicada que mapeia para **8009**.
5. Cole todas as variáveis de ambiente (secção acima).

### Ordem de arranque (automática)

O `docker/entrypoint.sh`:

1. Valida variáveis obrigatórias.
2. Executa `scripts/check_db.py` — **falha** se SQLite/PostgreSQL não estiver acessível.
3. `python manage.py migrate --noinput`
4. `python manage.py collectstatic --noinput --clear`
5. Inicia **Gunicorn** em `0.0.0.0:8009`

## 6. Healthcheck

- **HTTP**: `GET /health/` → corpo `OK` (sem dependência da BD no endpoint).
- O **Dockerfile** usa `curl` contra `http://127.0.0.1:8009/health/`.

## 7. Desenvolvimento local (sem Docker)

Não defina `DJANGO_PRODUCTION=1`: o projeto continua a usar **SQLite** em `db.sqlite3` e `runserver` como antes.

## 8. Requisitos Python

Ver `requirements.txt` (inclui `gunicorn`, `psycopg2-binary`, `whitenoise` para produção).

## 9. Segurança

- `DEBUG=False` em produção (definido pela imagem + `DJANGO_DEBUG=0`).
- `SECRET_KEY` obrigatória e não pode começar por `django-insecure-` em produção.
- Cookies `Secure` quando `DEBUG=False` (ajustável com `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`).

## 10. Bind mount `/app/media` (SQLite)

- Com **`DJANGO_USE_SQLITE=1`**, o ficheiro da base fica em **`SQLITE_PATH`** (por defeito **`/app/media/db.sqlite3`**).
- O bind mount **Host `.../volumes/db` → Container `/app/media`** é o cenário esperado: o SQLite fica nessa pasta persistente.
- **Uploads** usam **`/app/media/uploads`** por defeito (subpasta), para não misturar com `db.sqlite3`.

## 11. PostgreSQL: `DB_HOST` não é caminho de pasta

- **`DB_HOST`** é **hostname/IP** do serviço Postgres na rede Docker, **não** `/etc/easypanel/...`.

## 12. Erro: `DB_HOST não definida` (só modo PostgreSQL)

Se **não** usares SQLite, no serviço da **app** define `DB_*` ou `DATABASE_URL` / `POSTGRES_*`, mais `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `DJANGO_PRODUCTION=1`, `DJANGO_DEBUG=0`.

**Com SQLite**, define **`DJANGO_USE_SQLITE=1`** — não precisas de `DB_HOST`.

## 13. Problemas frequentes

| Sintoma | Causa provável |
|---------|----------------|
| `DB_HOST não definida` | Modo PostgreSQL sem `DB_*` — ou ativa **`DJANGO_USE_SQLITE=1`**. |
| Pasta `/app/media` não existe | Bind mount não aplicado ou caminho errado no EasyPanel. |
| Container reinicia logo | PostgreSQL inacessível (modo PG) ou volume sem permissão (SQLite). |
| 400 Bad Request / CSRF | Preencher `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS` com o domínio real. |
| Redirect HTTP/HTTPS errado | Ativar `USE_X_FORWARDED_PROTO=1` atrás do proxy. |
