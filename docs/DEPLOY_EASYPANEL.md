# Deploy RTT-IT no EasyPanel (Docker + PostgreSQL externo)

Este projeto corre em **produção** com:

- **Python 3.12** (imagem `python:3.12-slim-bookworm`)
- **Gunicorn** em `0.0.0.0:8009`
- **PostgreSQL externo** (serviço criado no EasyPanel ou outro host — **não** SQLite)
- **WhiteNoise** para ficheiros estáticos após `collectstatic`
- **Healthcheck**: `GET /health/`

## 1. Base de dados (PostgreSQL)

1. No EasyPanel, crie uma instância **PostgreSQL** (ou use um servidor gerido).
2. Crie manualmente a **base de dados** e o **utilizador** com permissões sobre essa BD.
3. Anote: `host`, `porta` (geralmente `5432`), `database`, `user`, `password`.

O container da aplicação **não cria** a base de dados. Se a BD não existir ou as credenciais estiverem erradas, o **entrypoint falha** com mensagem explícita e o container não sobe.

## 2. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha. No EasyPanel, defina as mesmas variáveis no serviço da app.

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DJANGO_PRODUCTION` | Sim (Docker) | Deve ser `1` — a imagem já define por defeito. |
| `DJANGO_DEBUG` | Sim | `0` em produção. |
| `DJANGO_SECRET_KEY` | Sim | Chave secreta forte (não use a de desenvolvimento). |
| `ALLOWED_HOSTS` | Sim | Domínios/IP separados por vírgula (sem `*`). |
| `DB_HOST` | Sim | Host do PostgreSQL. |
| `DB_PORT` | Não | Por defeito `5432`. |
| `DB_NAME` | Sim | Nome da base de dados. |
| `DB_USER` | Sim | Utilizador PostgreSQL. |
| `DB_PASSWORD` | Sim | Palavra-passe. |
| `CSRF_TRUSTED_ORIGINS` | Recomendado | URLs `https://...` separadas por vírgula. |
| `USE_X_FORWARDED_PROTO` | Recomendado | `1` se o proxy terminar HTTPS. |

## 3. Build e arranque (Docker local)

```bash
cp .env.example .env
# Edite .env com valores reais

docker compose build
docker compose up -d
```

A app escuta na porta **8009** do container; o `docker-compose.yml` mapeia `8009:8009`.

## 4. EasyPanel — App Docker

1. Crie um novo **App** do tipo Docker (build a partir do repositório ou imagem).
2. **Dockerfile**: na raiz do projeto (`Dockerfile`).
3. **Porta interna do container**: **8009** (Gunicorn).
4. No proxy reverso do EasyPanel, aponte para a porta publicada que mapeia para **8009**.
5. Cole todas as variáveis de ambiente (secção acima).

### Ordem de arranque (automática)

O `docker/entrypoint.sh`:

1. Valida variáveis obrigatórias.
2. Executa `scripts/check_db.py` — **falha** se não conseguir `SELECT 1` no PostgreSQL.
3. `python manage.py migrate --noinput`
4. `python manage.py collectstatic --noinput --clear`
5. Inicia **Gunicorn** em `0.0.0.0:8009`

## 5. Healthcheck

- **HTTP**: `GET /health/` → corpo `OK` (sem dependência da BD no endpoint).
- O **Dockerfile** usa `curl` contra `http://127.0.0.1:8009/health/`.

## 6. Desenvolvimento local (sem Docker)

Não defina `DJANGO_PRODUCTION=1`: o projeto continua a usar **SQLite** em `db.sqlite3` e `runserver` como antes.

## 7. Requisitos Python

Ver `requirements.txt` (inclui `gunicorn`, `psycopg2-binary`, `whitenoise` para produção).

## 8. Segurança

- `DEBUG=False` em produção (definido pela imagem + `DJANGO_DEBUG=0`).
- `SECRET_KEY` obrigatória e não pode começar por `django-insecure-` em produção.
- Cookies `Secure` quando `DEBUG=False` (ajustável com `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`).

## 9. Problemas frequentes

| Sintoma | Causa provável |
|---------|----------------|
| Container reinicia logo | PostgreSQL inacessível, credenciais erradas ou BD não criada — ver logs do entrypoint. |
| 400 Bad Request / CSRF | Preencher `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS` com o domínio real. |
| Redirect HTTP/HTTPS errado | Ativar `USE_X_FORWARDED_PROTO=1` atrás do proxy. |
