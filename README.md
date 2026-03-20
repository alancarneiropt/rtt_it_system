# RTT-IT — Gestão de Registos de Tempo em Tempo Real

Sistema de gestão de registos de tempo para colaboradores externos de TI. Backend em **Django**. Em desenvolvimento usa **SQLite**; em **produção (Docker)** usa **PostgreSQL externo**.

## Produção (Docker / EasyPanel)

- `Dockerfile`, `docker-compose.yml`, `.env.example`
- Documentação: **[docs/DEPLOY_EASYPANEL.md](docs/DEPLOY_EASYPANEL.md)**
- Porta interna: **8009** (Gunicorn)
- Health: **`GET /health/`**

## Requisitos

- Python 3.10+
- Django 4.2+

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

## Base de dados e superutilizador

```bash
python manage.py migrate
python manage.py createsuperuser
```

O utilizador root (superuser) usa o backoffice em `/admin/`; pode fazer login com **email** e palavra-passe (após configurar o email no perfil ou no user).

## Executar o servidor

```bash
python manage.py runserver
```

- **API base:** `http://127.0.0.1:8000/api/`
- **Admin (backoffice):** `http://127.0.0.1:8000/admin/`

## API

### Autenticação

- **POST** `/api/login/`  
  Body (JSON): `email`, `palavra_passe`  
  Resposta: sucesso/falha; em caso de sucesso a sessão é mantida por cookie.

### Marcações (autenticação obrigatória)

- **POST** `/api/marcacoes/`  
  Body (JSON): `latitude`, `longitude`, `tipo_marcacao`  
  `tipo_marcacao`: `entrada` | `inicio_almoco` | `fim_almoco` | `fim_jornada`

- **GET** `/api/marcacoes/minhas/`  
  Lista as marcações do utilizador logado (mais recentes primeiro), com "Data e Hora", "Tipo de Marcação" e `status: "registado"`.

### Utilizadores

- **POST** `/api/utilizadores/`  
  Body (JSON): `nome`, `email`, `palavra_passe`  
  Cria novo utilizador. Em conflito de email: "Email já registado."

### Relatórios (autenticação obrigatória)

- **GET** `/api/relatorios/marcacoes/`  
  Parâmetros (opcionais): `utilizador_id`, `data_inicio`, `data_fim` (formato `YYYY-MM-DD`).  
  Resposta: linha do tempo com `tipo` e `hora` de cada marcação.

- **GET** `/api/relatorios/exportar_csv/`  
  Mesmos filtros; devolve ficheiro CSV (Utilizador, Tipo de Marcação, Data/Hora, Latitude, Longitude).

## Backoffice (`/admin/`)

- **Utilizadores:** ver/editar utilizadores e perfil (nome).
- **Marcações:** ver todas as marcações (Utilizador, Tipo, Data/Hora, Localização, link para mapa).
- Tema: cor primária **#2563EB**, texto **#1A1A1A**, fundo **#F8FAFC**, fonte **Inter**.

## Modelos

- **User** (Django): `id`, `username`, `email`, `password`, `is_staff`, `is_active`, `date_joined`, `last_login`.
- **Profile**: `user` (OneToOne), `nome` (CharField 255).
- **Marcacao**: `id` (UUID), `utilizador` (FK User), `tipo`, `latitude`, `longitude`, `timestamp` (auto).

## Licença

Uso interno / portfolio.
