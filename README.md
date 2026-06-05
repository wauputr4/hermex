# Hermex Fun

**Hermex Fun** is an open-source astrology learning game for reflective
self-discovery.

Hermex helps people enter birth data, explore a natal chart, learn basic
astrology concepts, and receive a concise AI-assisted reflection. The goal is
not fortune-telling. Hermex is designed as a playful, educational, and
non-deterministic way to understand patterns, strengths, interests, relationship
themes, and career exploration.

Website target: **https://hermex.fun**

Repository: **https://github.com/wauputr4/hermex**

## What Hermex is for

Hermex is useful for:

- Learning astrology through a friendly product experience.
- Creating a simple natal chart from birth date, time, and place.
- Exploring zodiac signs, planets, houses, and aspects in plain language.
- Turning chart signals into reflective prompts and personal insights.
- Saving guest history locally so one-time visitors can come back later.
- Publishing a lightweight astrology profile page, similar to a bio link.
- Collecting feedback to improve the AI interpretation quality.
- Running a self-hosted astrology education MVP with your own AI provider.

Hermex is intentionally open source. Self-hosted users can run the community
edition with their own infrastructure and AI credentials.

## MVP features

- Mobile-first SvelteKit app with installable PWA behavior.
- Offline-friendly guest experience with local storage.
- Birth profile form with city search, latitude, longitude, and timezone data.
- Natal chart calculation using Swiss Ephemeris.
- SVG natal-wheel visualization.
- AI-assisted Hermes interpretation using an OpenAI-compatible provider.
- Structured insight cards for strengths, weaknesses, love, interests, talents,
  career direction, and last-5-year roadmap.
- Astrology education pages for planets, zodiac signs, houses, and aspects.
- Berita Langit article/calendar concept for astrology education content.
- Guest profile, history, and public shortlink-style profile flow.
- Admin dashboard for prompt editing, provider settings, usage limits, feedback,
  logs, and content management.
- Entitlement-ready usage layer for future hosted subscription/billing without
  embedding private payment-provider code in the public repo.

## Project status

Hermex is currently in **beta MVP**.

The project is ready for experimentation, self-hosting, and contribution, but
the product should still be treated as an evolving educational prototype.

## Quick start

### Backend

```bash
cd backend
cp .env.example .env
python3.11 -m pip install -r requirements.txt
python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 5667 --reload
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 5666
```

Open:

```text
http://127.0.0.1:5666
```

The local frontend proxies API and admin routes to the backend.

## Admin dashboard

Local dashboard:

```text
http://127.0.0.1:5666/admin/dashboard
```

Default local credentials:

```text
username: admin
password: hermes-admin
```

Change the admin password and session secret before any hosted deployment.

## Environment setup

Backend variables are documented in:

- [backend/.env.example](backend/.env.example)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md)

Frontend variables are documented in:

- [frontend/.env.example](frontend/.env.example)

Google Analytics is opt-in through `VITE_GA_MEASUREMENT_ID`; leave it empty for
self-hosted deployments that should not report usage to the hosted property.

Never commit real API keys, OAuth secrets, admin passwords, or production
session secrets.

## Deployment and PWA cache

Because Hermex is a PWA, production deployments must handle service worker
cache, browser cache, and local guest storage carefully.

Read the deployment checklist before releasing:

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

That guide includes cache headers, service worker update notes, local storage
migration guidance, reverse proxy notes, and release smoke-test steps.

## Documentation

- [docs/PLAN.md](docs/PLAN.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

Public legal pages for hosted OAuth verification:

- `https://hermex.fun/terms`
- `https://hermex.fun/privacy`

## Contributing

Issues and pull requests are welcome.

Good contributions include:

- Improving mobile UI and accessibility.
- Improving astrology education content.
- Improving natal chart visualization.
- Hardening auth, sessions, rate limits, and deployment docs.
- Adding tests around chart calculation, profile publishing, and admin flows.
- Improving PWA offline and update behavior.

Please avoid committing real user data, secrets, or provider-specific private
billing code.

## Ethics

Hermex is a reflective game and education tool. It should support curiosity,
self-understanding, and personal development.

Hermex should not be used as deterministic advice for medical, legal,
financial, or life-critical decisions.

## License

MIT
