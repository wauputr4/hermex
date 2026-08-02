# Hermex Technical Architecture

## 1) High-level architecture

Hermex is organized into two main services:

- **Frontend (SvelteKit + SVG/CSS interaction)**
  - Handles the focused birth form, rating questionnaire, guest preview, authenticated character card, natal detail, and astrology education.
  - Stores only the pending profile claim, questionnaire answers, editable username, and interpretation id needed to resume Google OAuth.
- **Backend (FastAPI + SQLite)**
  - Handles data validation, natal calculation, personality-signal derivation, questionnaire validation, Google ownership, and LLM orchestration.
  - Stores profiles, account links, feedback, admin settings, and interpretation history.

## 2) Main data flow

```text
User submits birth date, optional time, and selected city
  -> FE calls POST /api/v1/birth/analyze
  -> City picker provides latitude, longitude, and timezone
  -> Natal chart calculation uses the supplied time or a disclosed 00:00 fallback
  -> Backend derives 10 internal personality signals
  -> Configured AI creates 10 plain-language rating questions in the backend
     (local/test can use a deterministic fallback)
  -> Browser receives one question id and prompt at a time plus the 1–5 scale
  -> User answers every item from 1 to 5
  -> FE calls POST /api/v1/birth/validate, then POST /api/v1/interpretation
  -> Guest receives only a preview and three editable username suggestions
  -> Google OAuth links the profile claim to the signed-in account
  -> Authenticated owner fetches GET /api/v1/interpretations/{id}/full
  -> FE shows the character card; natal and narrative details open through Lihat lengkap
```

## 3) Backend modules

### 3.1 `birth_analysis`
- `BirthProfileInput`: Pydantic input schema.
- `normalize_birth_data`: normalize date/place/time to UTC-safe representation.
- `compute_chart`: wrapper around `pyswisseph`.
- `build_trait_profile`: convert chart into interest/talent scores.

### 3.2 `astrology`
- `planet_service`: compute major planet longitudes plus extended depth points when Swiss Ephemeris supports them.
- `house_service`: house calculations (ascendant + cusps).
- `aspect_service`: major aspects (conjunction, trine, sextile, square, opposition).

### 3.3 `questionnaire`
- `derive_personality_signals`: derives the 10 internal chart components.
- `build_questionnaire`: asks the configured AI provider for prompts without astrology terms.
- A deterministic fallback keeps local development and tests runnable without a provider.
- `validate_questionnaire_answers`: requires each answer exactly once as an integer from 1 to 5.

### 3.4 `llm`
- `llm_client`: OpenAI-compatible client adapter.
- `interpret_prompt_builder`: builds deterministic, constrained prompts.
- `cache_safe_response`: stores safe textual interpretation and prompt metadata.

### 3.5 `auth and ownership`
- Signed Google sessions identify hosted users.
- Profile claim tokens link a guest analysis to an authenticated account.
- Full interpretations are returned only to the linked owner; guest and public payloads expose previews only.

## 4) Data model (MVP)

### Core tables

- `profiles`
  - `id`, `display_name` (nullable), `birth_date`, `birth_time` (nullable), `birth_place`,
  - `latitude`, `longitude`, `timezone`, `time_unknown` (boolean), `created_at`
- `interpretations`
  - `id`, `profile_id`, `provider`, `model`, `prompt_hash`, `response_json`, `request_payload_json`, `created_at`
- `user_profiles`
  - `user_sub`, `profile_id`, `linked_at`
  - links a claimed guest profile to the Google account allowed to open its full interpretation
- `settings`
  - `key`, `value`, `updated_at`
  - stores local admin-editable prompt, AI provider settings, and usage limits
- `feedback`
  - `id`, `profile_id`, `interpretation_id`, `rating`, `message`, `source`, `created_at`

## 5) API contract (MVP)

### `POST /api/v1/birth/analyze`
Request:
- `display_name` (string, optional)
- `birth_date` (ISO date, required)
- `birth_time` (HH:mm, optional)
- `birth_place` (string, required)
- `latitude`, `longitude` (optional, fallback if geocode fails)
- `timezone` (optional, only if user provides manual timezone)

Response:
- `profile_id`
- `claim_token` for the post-OAuth ownership link
- `precision` with the effective-time caveat
- `questionnaire` with the question count, 1–5 scale, and first `{id, prompt, index}` item

The initial public response does not include internal chart signals, the system
prompt, or the remaining generated questions. The displayed prompt text is
necessarily inspectable in the browser.

### `POST /api/v1/birth/question`
- Input: `profile_id`, its `claim_token`, and the requested question index.
- Returns only the requested `{id, prompt, index}` plus count and scale.
- Rejects an invalid profile claim token.

### `POST /api/v1/birth/validate`
- Input: `profile_id`, its `claim_token`, and an answer for every question id.
- Rejects missing, extra, non-integer, or out-of-range answers.
- Response: updated confidence and readiness for interpretation.

### `POST /api/v1/interpretation`
- Input: `profile_id`, `language`.
- Requires the completed questionnaire.
- Guest response contains only `preview_summary`, three highlights, three editable username suggestions, confidence, and caveat.
- The complete result remains server-side.

### `GET /api/v1/interpretations/{interpretation_id}/full`
- Requires a Google session and a profile linked through its claim token.
- Returns the complete structured analysis only to the profile owner.
- `SELF_HOSTED_FULL_ACCESS=true` is the explicit self-hosted bypass.

### `POST /api/v1/interpretation/ask`
- Input: `profile_id`, `language`, `question`.
- Requires profile ownership and returns a detailed answer based on the saved payload.

### `POST /api/v1/feedback`
- Input: `profile_id`, `interpretation_id`, `rating`, optional message.
- Response: saved feedback id.

### `GET /api/v1/admin/guest-history`
- Admin-only guest history with prompt payload and latest AI response.

### `POST /api/v1/admin/prompt`
- Admin-only system prompt update.

### `POST /api/v1/admin/llm-config`
- Admin-only provider/base URL/API key/model configuration plus request-per-minute, request-per-day, and max-token limits.

### `POST /api/v1/admin/llm-models`
- Admin-only model sync from an OpenAI-compatible `/models` endpoint.

## 6) Non-functional requirements

- API chart calculation should respond within 3 seconds for 95% of valid requests.
- Same input must produce consistent chart output.
- LLM prompts and responses must be auditable and stored with model metadata.
- Guest, public-profile, and unauthenticated API responses must never expose `full_analysis`.
- AI calls should be rate-limited according to admin settings before provider requests are sent.
- Network failures should preserve the current form state and explain how to retry.
- Input sanitation and timezone checks must protect against malformed birth payloads.

## 7) Future considerations

- Move heavy jobs to async workers if chart/LLM usage rises.
- Move from SQLite to PostgreSQL as data growth requires.
- Add response caching for repeated identical birth payloads.
