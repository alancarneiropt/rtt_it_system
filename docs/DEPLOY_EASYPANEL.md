# Deploy RTT-IT no EasyPanel (Docker + SQLite)

- **Python 3.12**, **Gunicorn** `0.0.0.0:8009`
- **Base de dados:** apenas **SQLite** em ficheiro persistente
- **Caminho por defeito no container:** `/app/media/db.sqlite3`
- **WhiteNoise** para estáticos; **health:** `GET /health/`

## 1. Bind mount (EasyPanel)

No serviço **APP**:

| Caminho no host (exemplo) | Caminho no container |
|---------------------------|----------------------|
| `/etc/easypanel/projects/.../volumes/db` | `/app/media` |

O ficheiro da base fica em **`/app/media/db.sqlite3`**. Uploads usam **`/app/media/uploads`**.

## 2. Variáveis de ambiente (app)

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DJANGO_PRODUCTION` | Sim (imagem) | Já vem `1` na imagem. |
| `DJANGO_DEBUG` | Sim | `0` em produção. |
| `DJANGO_SECRET_KEY` | Sim | Chave forte. |
| `ALLOWED_HOSTS` | Sim | Domínios, vírgula, sem `*`. |
| `SQLITE_PATH` | Não | Por defeito `/app/media/db.sqlite3`. |
| `CSRF_TRUSTED_ORIGINS` | Recomendado | `https://...` |
| `USE_X_FORWARDED_PROTO` | Recomendado | `1` atrás do proxy HTTPS. |

**Não** uses `DB_HOST`, PostgreSQL nem `DATABASE_URL`.

## 3. Arranque (entrypoint)

1. Confirma pasta `/app/media` (bind mount).
2. `scripts/check_db.py` — testa SQLite.
3. `migrate` → `collectstatic` → `manage.py check` → **Gunicorn**.

## 4. Problemas

| Sintoma | Causa |
|---------|--------|
| Pasta `/app/media` não existe | Bind mount não configurado. |
| Erro ao criar SQLite | Permissões no volume do host. |
| 400 / CSRF | `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS` corretos para o domínio. |

## 5. Docker local

```bash
cp .env.example .env
# Preencher DJANGO_SECRET_KEY e ALLOWED_HOSTS
docker compose up -d --build
```

Mapeie um volume local para `/app/media` se quiser persistir a BD.
