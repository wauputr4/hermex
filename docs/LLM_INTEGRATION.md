# LLM Integration

Hermex uses an OpenAI-compatible chat-completions API to create the
chart-informed questionnaire and the narrative interpretation. Natal
calculation stays in the backend chart engine.

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
http://127.0.0.1:5666/admin/dashboard
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

## Questionnaire generation

When a provider is configured, the backend sends its internal personality
signals to the provider and requests ten plain-language statements rated from
1 to 5. Questions must not expose astrology terminology. A deterministic
fallback keeps local development and automated tests runnable without an AI
provider.

The public analyze response contains the scale and only the first
`{id, prompt, index}` item. Later questions are requested one at a time using the
profile claim token. Prompt text currently shown in the browser can be inspected;
raw chart signals, the system prompt, remaining questions, and the provider's
full payload are not included in the initial response.

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

## Interpretation prompt payload

The user message includes:

- profile id,
- selected language,
- birth context,
- planets,
- zodiac signs,
- Placidus houses when available,
- aspects,
- derived traits,
- personality signals,
- validated questionnaire answers.

## Required interpretation response JSON

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
