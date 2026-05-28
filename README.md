# Hermex Quest

**Hermex Quest** is an open-source astrology learning game and reflective self-discovery MVP.

Website/domain target: **https://hermex.fun**

Repository: **https://github.com/wauputr4/hermex**

Hermex is intentionally open source: self-hosted users can run the full community edition with their own infrastructure and AI provider credentials.

Hermex turns birth context into a natal chart, shows readable astrology signals, and asks a configurable OpenAI-compatible AI provider to generate concise, non-deterministic reflections around strengths, love, interests, talents, career direction, and a last-5-year roadmap.

## MVP highlights

- Mobile-first SvelteKit interface with installable-app feel.
- PWA manifest and service worker so Hermex can be installed from the browser.
- Offline PWA fallback page plus in-app offline mode for saved guest history and education.
- Guest-first local storage for draft birth data and local guest chart history.
- Local guest game progress with XP, streak, and badge storage.
- Searchable birth-city picker with latitude, longitude, and timezone metadata.
- Swiss Ephemeris natal chart calculation with Placidus houses when birth time and coordinates are available.
- SVG natal-wheel visualization, expanded planet cards, and aspect list.
- Interactive astrology education page for planets, zodiac signs, houses, and aspects.
- Google OAuth terms page placeholder for hosted account login.
- Public legal pages for Google OAuth verification: `/terms` and `/privacy`.
- AI interpretation page with highlighted summary, focused insight cards, roadmap, and user feedback.
- Bottom navigation for Profile, Connect/share, and Hermex AI detail questions.
- Local admin dashboard for overview, guest history, feedback, logs, prompt editing, and AI provider configuration.
- OpenAI-compatible provider support with custom base URL, API key, model, temperature, max tokens, and model sync from `/models`.
- Admin-controlled AI usage limits for requests per minute, requests per day, and max tokens.

## Stack

- Frontend: SvelteKit, TypeScript, SVG/CSS animation.
- Backend: FastAPI, SQLite, Pydantic, HTTPX.
- Astrology: `pyswisseph` for Swiss Ephemeris chart math.
- AI: OpenAI-compatible HTTP API.
- License: MIT.

## Repository structure

```text
hermex/
├─ backend/
│  ├─ app/main.py
│  ├─ requirements.txt
│  ├─ requirements-optional.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  ├─ static/
│  ├─ package.json
│  └─ .env.example
├─ docs/
│  ├─ PLAN.md
│  ├─ ARCHITECTURE.md
│  ├─ DEVELOPMENT.md
│  └─ LLM_INTEGRATION.md
├─ CONTRIBUTING.md
├─ SECURITY.md
├─ CODE_OF_CONDUCT.md
├─ LICENSE
└─ README.md
```

## Quick start

### 1. Backend

```bash
cd backend
cp .env.example .env
python3.11 -m pip install -r requirements.txt
python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 18080 --reload
```

Backend URL:

```text
http://127.0.0.1:18080
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 18173
```

Frontend URL:

```text
http://127.0.0.1:18173
```

## Environment variables

Backend configuration lives in `backend/.env`:

```env
LLM_PROVIDER=openai_compat
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.4
LLM_MAX_TOKENS=700
LLM_REQUESTS_PER_MINUTE=6
LLM_REQUESTS_PER_DAY=40

SQLITE_URL=sqlite:///./hermex.db
CORS_ORIGINS=http://localhost:18173,http://127.0.0.1:18173
PUBLIC_APP_URL=https://hermex.fun

ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
ADMIN_SESSION_SECRET=change_this_session_secret

GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://hermex.fun/api/v1/auth/google/callback
GOOGLE_SESSION_SECRET=change_this_google_session_secret
```

Never commit real API keys. Runtime secrets are intentionally ignored by `.gitignore`.

## Admin dashboard

Local dashboard:

```text
http://127.0.0.1:18080/admin/dashboard
```

Default local credentials:

```text
username: admin
password: hermes-admin
```

Change them with:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password
ADMIN_SESSION_SECRET=change_this_session_secret
```

The dashboard supports:

- Guest history.
- Prompt payload sent to AI.
- Latest AI response.
- Editable Hermes system prompt.
- AI provider configuration.
- Custom OpenAI-compatible endpoint.
- API key input.
- Model sync from the configured endpoint's `/models` route.
- Usage limits for AI requests per minute, AI requests per day, and max tokens.
- Feedback and log menus with guest export for local auditing.

## API overview

- `GET /api/v1/health`
- `POST /api/v1/birth/analyze`
- `POST /api/v1/birth/validate`
- `GET /api/v1/profiles/{profile_id}`
- `POST /api/v1/interpretation`
- `POST /api/v1/interpretation/ask`
- `POST /api/v1/feedback`
- `GET /api/v1/auth/google/start`
- `GET /api/v1/auth/google/callback`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/logout`
- `POST /api/v1/quests/start`
- `POST /api/v1/quests/complete`
- `GET /api/v1/roadmap/{profile_id}`
- `GET /api/v1/admin/guest-history`
- `POST /api/v1/admin/prompt`
- `POST /api/v1/admin/llm-config`
- `POST /api/v1/admin/llm-models`

Admin endpoints require dashboard login or HTTP Basic auth.

## AI response contract

Hermes asks the provider for valid JSON with:

- `summary`
- `strengths`
- `weaknesses`
- `love`
- `interests`
- `talents`
- `careers`
- `five_year_roadmap`
- `development_plan`
- `confidence`

The app treats astrology as symbolic reflection and learning material, not deterministic prediction.

## Documentation

- Public Terms URL for OAuth setup: `https://hermex.fun/terms`
- Public Privacy URL for OAuth setup: `https://hermex.fun/privacy`
- [docs/PLAN.md](docs/PLAN.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Contributing

Issues and pull requests are welcome. Please keep changes small, explain the user-facing behavior, and avoid committing real user data or secrets.

## Ethics

Hermex is a reflective game and education tool. It should support self-understanding, curiosity, and personal development. It should not be used as deterministic advice for medical, legal, financial, or life-critical decisions.
