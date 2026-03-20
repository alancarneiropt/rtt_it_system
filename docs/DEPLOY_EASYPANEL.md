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
2. **Como root:** `chown -R appuser:appuser /app/media` — volumes no host vêm muitas vezes como `root:root`; sem isto o SQLite dá *attempt to write a readonly database* (ex.: login backoffice ao gravar sessão).
3. `scripts/check_db.py` — testa SQLite (como `appuser`).
4. `migrate` → `collectstatic` → `manage.py check` → **Gunicorn** (como `appuser`).

**Nota:** o contentor inicia o script como **root** só para este `chown`; o processo Gunicorn corre como **`appuser`**. Se o painel forçar *run as non-root* sem root no arranque, ajuste no **host** o dono da pasta do volume para o UID do utilizador do contentor ou desative essa restrição para esta app.

## 4. Problemas

| Sintoma | Causa |
|---------|--------|
| Pasta `/app/media` não existe | Bind mount não configurado. |
| Erro ao criar SQLite | Permissões no volume do host. |
| `attempt to write a readonly database` | Volume montado só de leitura para a app; o entrypoint faz `chown` de `/app/media` para `appuser` se arrancar como root. Ver nota acima. |
| 400 / CSRF | `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS` corretos para o domínio. |

## 5. Docker local

```bash
cp .env.example .env
# Preencher DJANGO_SECRET_KEY e ALLOWED_HOSTS
docker compose up -d --build
```

Mapeie um volume local para `/app/media` se quiser persistir a BD.
