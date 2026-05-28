# LLM Integration

Hermex uses an OpenAI-compatible chat-completions API for narrative interpretation. Astrology math stays in the backend chart engine; the LLM only turns chart data into readable, constrained reflection.

## Configuration sources

Hermex reads provider configuration from:

1. `backend/.env`
2. local SQLite settings saved from the admin dashboard

SQLite settings override `.env` values for local MVP testing.

## Environment variables

```env
LLM_PROVIDER=openai_compat
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.4
LLM_MAX_TOKENS=700
```

## Admin dashboard provider menu

Open:

```text
http://127.0.0.1:18080/admin/dashboard
```

The dashboard can update:

- provider type,
- custom base URL,
- API key,
- model,
- temperature,
- max tokens.

The **Sync models** button calls:

```text
POST /api/v1/admin/llm-models
```

That endpoint calls the configured provider at:

```text
GET {LLM_BASE_URL}/models
```

## Chat-completions call

Hermex calls:

```text
POST {LLM_BASE_URL}/chat/completions
```

Payload shape:

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "{...chart payload...}" }
  ],
  "temperature": 0.4,
  "max_tokens": 700,
  "stream": false
}
```

## Prompt payload

The user message includes:

- profile id,
- selected language,
- birth context,
- planets,
- zodiac signs,
- Placidus houses when available,
- aspects,
- derived traits,
- roadmap preview,
- validation answers.

## Required response JSON

The provider should return valid JSON with:

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

The frontend normalizes object items into strings so imperfect provider output does not leak `[object Object]` into the UI.

## Failure behavior

If the provider cannot be reached, the frontend routes to a dedicated AI connection error page instead of showing fallback text as if it were an AI interpretation.

## Safety rules

- Never commit real API keys.
- Never print stored API keys back in the admin dashboard.
- Keep AI output framed as reflection, not deterministic prediction.
- Keep prompt payloads auditable in the local dashboard for MVP debugging.
