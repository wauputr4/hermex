# Hermex Technical Architecture

## 1) High-level architecture

Hermex is organized into two main services:

- **Frontend (SvelteKit + SVG/CSS interaction)**
  - Handles birth form, profile summary screens, astrology education, and installable-app style UI.
  - Manages local UI state, guest draft/history storage, PWA install prompt, and backend API calls.
- **Backend (FastAPI + SQLite)**
  - Handles data validation, astrology computation, questionnaire scoring, and LLM orchestration.
  - Stores profiles, sessions, quests, and interpretation history.

## 2) Main data flow

```text
User submits birth input (name optional)
  -> FE calls POST /api/v1/birth/analyze
  -> API validates required fields (place + birth date, time optional)
  -> City picker provides latitude, longitude, and timezone
  -> Natal chart calculation (pyswisseph + Placidus houses when possible)
  -> Profile derivation (traits + aptitude + risk/uncertainty)
  -> Returns validation questionnaire when needed
  -> User submits questionnaire answers
  -> Backend merges validation signals
  -> Backend requests interpretation from configured LLM endpoint
  -> FE renders chart, insight cards, education cards, roadmap, and feedback UI
```

## 3) Backend modules

### 3.1 `birth_analysis`
- `BirthProfileInput`: Pydantic input schema.
- `normalize_birth_data`: normalize date/place/time to UTC-safe representation.
- `compute_chart`: wrapper around `pyswisseph`.
- `build_trait_profile`: convert chart into interest/talent scores.

### 3.2 `astrology`
- `planet_service`: compute major planet longitudes.
- `house_service`: house calculations (ascendant + cusps).
- `aspect_service`: major aspects (conjunction, trine, sextile, square, opposition).

### 3.3 `questionnaire`
- `questionnaire_loader`: loads profile-specific validation questions.
- `validation_scoring`: converts answers to confidence levels and ambiguity tags.
- `clarification_rules`: decides if additional prompts are required.

### 3.4 `llm`
- `llm_client`: OpenAI-compatible client adapter.
- `interpret_prompt_builder`: builds deterministic, constrained prompts.
- `cache_safe_response`: stores safe textual interpretation and prompt metadata.

### 3.5 `gameplay`
- `quest_generator`: map profile + questionnaire answers to quest paths.
- `progress_service`: updates progression and unlocked milestones.

## 4) Data model (MVP)

### Core tables

- `profiles`
  - `id`, `display_name` (nullable), `birth_date`, `birth_time` (nullable), `birth_place`,
  - `latitude`, `longitude`, `timezone`, `time_unknown` (boolean), `created_at`
- `interpretations`
  - `id`, `profile_id`, `provider`, `model`, `prompt_hash`, `response_json`, `request_payload_json`, `created_at`
- `user_quests`
  - `id`, `profile_id`, `quest_slug`, `status`, `score`, `completed_at`, `result_json`
- `settings`
  - `key`, `value`, `updated_at`
  - stores local admin-editable prompt and AI provider settings

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
- `chart` (planetary snapshot if available)
- `needs_validation` (boolean)
- `validation_questions` (array, if true)
- `traits` (partial, if available)
- `roadmap_preview` (partial suggestions based on available data)

### `POST /api/v1/birth/validate`
- Input: `profile_id`, `answers` map.
- Response: updated profile confidence and readiness for interpretation.

### `POST /api/v1/interpretation`
- Input: `profile_id`, `language`.
- Response: `interpretation` object from LLM, source metadata, and confidence level.

### `POST /api/v1/interpretation/ask`
- Input: `profile_id`, `language`, `question`.
- Response: detailed Hermes AI answer based on the saved chart payload.

### `POST /api/v1/feedback`
- Input: `profile_id`, `interpretation_id`, `rating`, optional message.
- Response: saved feedback id.

### `GET /api/v1/admin/guest-history`
- Admin-only guest history with prompt payload and latest AI response.

### `POST /api/v1/admin/prompt`
- Admin-only system prompt update.

### `POST /api/v1/admin/llm-config`
- Admin-only provider/base URL/API key/model configuration.

### `POST /api/v1/admin/llm-models`
- Admin-only model sync from an OpenAI-compatible `/models` endpoint.

### `POST /api/v1/quests/start`
- Input: `profile_id`, `quest_slug`.
- Response: quest state object.

### `POST /api/v1/quests/complete`
- Input: `quest_id`, `result_payload`.
- Response: reward, new score, next suggestion.

### `GET /api/v1/roadmap/{profile_id}`
- Response: roadmap data for 30/60/90 days + progress percentage.

## 6) Non-functional requirements

- API chart calculation should respond within 3 seconds for 95% of valid requests.
- Same input must produce consistent chart output.
- LLM prompts and responses must be auditable and stored with model metadata.
- Input sanitation and timezone checks must protect against malformed birth payloads.

## 7) Future considerations

- Move heavy jobs to async workers if chart/LLM usage rises.
- Move from SQLite to PostgreSQL as data growth requires.
- Add response caching for repeated identical birth payloads.
