# Hermex Deployment Guide

This guide covers the production checklist for a hosted Hermex deployment such
as `https://hermex.fun`, including browser cache and local guest storage.

## 1. Build targets

Hermex has two runtime surfaces:

- Frontend: SvelteKit web app served to users.
- Backend: FastAPI API, admin routes, auth callbacks, AI provider calls, and
  SQLite storage.

For local development the default ports are:

```text
frontend: http://127.0.0.1:5666
backend:  http://127.0.0.1:5667
```

For production, serve the public app from one HTTPS origin whenever possible:

```text
https://hermex.fun
```

Proxy these paths to the backend:

```text
/api/v1/*
/admin/*
```

Keeping frontend and backend on the same public origin reduces CORS friction,
cookie/session mismatch, and Google OAuth redirect complexity.

## 2. Required production environment variables

Set these backend variables for hosted deployments:

Frontend build variable:

```env
# Same-origin deployment through the reverse proxy.
# Leave empty only if your deployment intentionally uses relative API paths.
VITE_API_BASE=https://hermex.fun

# Optional. Enables Google Analytics only for builds where this is set.
# Leave empty for local development and self-hosted installs that should not
# report usage to the hosted Hermex Fun property.
VITE_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

Backend variables:

```env
PUBLIC_APP_URL=https://hermex.fun
CORS_ORIGINS=https://hermex.fun

SQLITE_URL=sqlite:///./hermex.db

LLM_PROVIDER=openai_compat
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace_with_private_key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.4
LLM_MAX_TOKENS=700
LLM_REQUESTS_PER_MINUTE=6
LLM_REQUESTS_PER_DAY=40

ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace_with_strong_password
ADMIN_SESSION_SECRET=replace_with_random_secret

GOOGLE_CLIENT_ID=replace_with_google_client_id
GOOGLE_CLIENT_SECRET=replace_with_google_client_secret
GOOGLE_REDIRECT_URI=https://hermex.fun/api/v1/auth/google/callback
GOOGLE_SESSION_SECRET=replace_with_random_secret

ENTITLEMENT_WEBHOOK_SECRET=replace_if_using_private_billing_service
```

Do not deploy default local secrets. Do not commit `.env` files.

## 3. Browser cache checklist

Hermex currently runs as a regular web app without a service worker. Generated
assets and HTML still need different cache policies.

Before each release:

1. Build the frontend from a clean checkout.
2. Make sure generated assets use hashed filenames.
3. Serve `index.html` with conservative caching.
4. Serve hashed assets with long-lived immutable caching.
5. After deploy, open the app in a fresh browser profile and an existing browser
   session to confirm both update correctly.

Recommended cache headers:

```text
/_app/immutable/* Cache-Control: public, max-age=31536000, immutable
/                Cache-Control: no-cache
/*.html          Cache-Control: no-cache
```

## 4. Browser cache recovery

If users report an old UI or API URL after deployment:

1. Ask them to reload Hermex.
2. If still stale, clear site data for `hermex.fun` and reopen the app.

## 5. Local storage and guest history

Hermex is guest-first. The frontend can store:

- Draft birth input.
- Local guest history.
- Public profile draft state.

Production deploys should avoid changing local storage keys casually. If a
breaking local data shape change is needed:

1. Add a versioned storage key or migration path.
2. Keep old data readable where possible.
3. Fall back safely when old local data cannot be parsed.
4. Never let invalid local storage block the user from opening the app.

Suggested convention:

```text
hermex:<feature>:v1
hermex:<feature>:v2
```

When adding a new storage version, keep the old reader for at least one beta
release so existing browser sessions can migrate naturally.

## 6. API and session safety

Use HTTPS in production. Set secure, HTTP-only session cookies from the backend
for admin and Google login flows.

Production expectations:

- `PUBLIC_APP_URL` matches the public frontend origin.
- `CORS_ORIGINS` contains only trusted hosted origins.
- Google OAuth redirect URI exactly matches Google Console configuration.
- Admin session secret and Google session secret are long random values.
- Admin password is not the local default.
- `/admin/*` and `/api/v1/admin/*` are protected.

## 7. Reverse proxy example

At a high level, a reverse proxy should serve the frontend and forward backend
paths:

```text
https://hermex.fun/              -> frontend build
https://hermex.fun/api/v1/*      -> backend
https://hermex.fun/admin/*       -> backend
```

Forward these headers to the backend:

```text
Host
X-Forwarded-Host
X-Forwarded-Proto
X-Forwarded-For
```

## 8. Release smoke test

After deployment:

1. Open `https://hermex.fun`.
2. Confirm `/terms` and `/privacy` load publicly.
3. Submit a guest chart with a real city.
4. Confirm AI errors are friendly if the provider limit is reached.
5. Confirm guest history appears locally after a successful analysis.
6. Confirm a network failure preserves form state and provides a retry path.
7. Login to `/admin/dashboard` on the same origin and confirm prompt/provider/settings pages work.

## 9. Self-hosted notes

Self-hosted users can ignore hosted billing and set:

```env
SELF_HOSTED_FULL_ACCESS=true
```

They should provide their own AI provider credentials and adjust usage limits to
match their infrastructure.
