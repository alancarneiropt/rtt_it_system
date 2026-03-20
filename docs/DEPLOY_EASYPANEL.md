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
| `DB_HOST` | Sim* | Host do PostgreSQL (hostname na rede Docker, **não** caminho de pasta). |
| `DB_PORT` | Não | Por defeito `5432`. |
| `DB_NAME` | Sim* | Nome da base de dados. |
| `DB_USER` | Sim* | Utilizador PostgreSQL. |
| `DB_PASSWORD` | Sim* | Palavra-passe. |

\* **Alternativa:** pode definir só `DATABASE_URL` (`postgresql://...`) ou `POSTGRES_HOST` + `POSTGRES_DB` + `POSTGRES_USER` + `POSTGRES_PASSWORD` — o **entrypoint** converte automaticamente para `DB_*` e regista tudo nos **logs em tempo real** (Fase 1/7).
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

## 9. Bind mount: pasta no VPS ≠ “caminho do PostgreSQL”

- **`DB_HOST` não é um caminho de pastas** (ex.: não uses `/etc/easypanel/...`). É o **nome de rede** ou **IP** do servidor PostgreSQL (ex.: hostname interno do serviço Postgres no EasyPanel, muitas vezes algo como `nome_do_servico_postgres` ou o nome do container na mesma rede Docker).
- Os **ficheiros de dados do PostgreSQL** ficam no **volume do serviço PostgreSQL** que o EasyPanel gere — não se montam na app Django como se fosse SQLite.
- Se montares no container da app:
  - **Host:** `/etc/easypanel/projects/.../volumes/db` (ou outra pasta tua)
  - **Container:** `/app/media`  
  isso serve para **`MEDIA_ROOT`** (uploads / ficheiros da app), **não** para ligar o Django ao Postgres.

`MEDIA_ROOT` por defeito é `BASE_DIR / 'media'` (= `/app/media` no Docker). Opcional: variável `MEDIA_ROOT` se quiseres outro caminho.

## 10. Erro: `ERRO: Variável obrigatória DB_HOST não definida`

No EasyPanel, no **serviço da aplicação** (não só no Postgres), adiciona **Environment** / variáveis:

- `DB_HOST` = hostname/IP do Postgres (copiar do painel do serviço PostgreSQL no EasyPanel)
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` (se não for 5432)
- `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `DJANGO_PRODUCTION=1`, `DJANGO_DEBUG=0`

Sem isto, o `entrypoint` **aborta de propósito** antes de subir o Gunicorn.

## 11. Problemas frequentes

| Sintoma | Causa provável |
|---------|----------------|
| `DB_HOST não definida` | Faltam variáveis de ambiente na **app** no EasyPanel. |
| Container reinicia logo | PostgreSQL inacessível, credenciais erradas ou BD não criada — ver logs do entrypoint. |
| 400 Bad Request / CSRF | Preencher `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS` com o domínio real. |
| Redirect HTTP/HTTPS errado | Ativar `USE_X_FORWARDED_PROTO=1` atrás do proxy. |
