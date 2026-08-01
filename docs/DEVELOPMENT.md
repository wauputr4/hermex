# Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Git

## Backend setup

```bash
cd backend
cp .env.example .env
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5667
```

Backend URL:

```text
http://127.0.0.1:5667
```

Admin dashboard:

```text
http://127.0.0.1:5666/admin/dashboard
```

Use this frontend URL for admin access. The existing Vite proxy forwards
`/admin/*` to the backend on port `5667`.

Default local admin credentials:

```text
admin / hermes-admin
```

Change the credentials in `backend/.env` before using this outside local development.

## Frontend setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 5666
```

Frontend URL:

```text
http://127.0.0.1:5666
```

## AI provider setup

You can configure the AI provider in two ways:

- Environment variables in `backend/.env`.
- Admin dashboard form under **Hermes AI provider**.

The dashboard can save:

- provider type,
- OpenAI-compatible base URL,
- API key,
- model,
- temperature,
- max tokens.

It can also sync model options from the configured endpoint's `/models` route.

## Local smoke flow

1. Open the frontend.
2. Fill the birth date, optional time, and city.
3. Click **Mulai Analisis** and complete the 1–5 questionnaire.
4. Confirm the guest preview and username recommendations appear.
5. Login with Google and confirm the complete analysis and natal-chart detail are available.
6. Check `/admin/dashboard` on port `5666` for the saved analysis and prompt payload.

## Recommended quality tools

- Backend syntax check: `python3.11 -m py_compile backend/app/main.py`
- Backend tests, when added: `python -m pytest`
- Frontend build: `npm run build`

## Workflow

1. Create a feature branch from `main`.
2. Keep feature scope small and update related docs.
3. If API changes, update `README.md` and `docs/ARCHITECTURE.md`.
4. Do not commit real `.env` files, SQLite databases, user data, or API keys.
5. For UI changes, include screenshots or reproduction notes in the pull request.
