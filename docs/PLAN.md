# Hermex Open Source Development Plan

This plan is optimized for a small team or solo maintainer.

## Vision

Build a lightweight personality analysis flow with clear birth inputs and practical, confidence-aware insights.

## MVP target (8 weeks)

### Weeks 1–2: Foundation
- Initialize FE + BE monorepo.
- Configure baseline CI for lint/tests.
- Implement `POST /api/v1/birth/analyze`.
- Create birth input UI and basic validation.
- Persist profiles and sessions in SQLite.

### Weeks 3–4: Birth + Questionnaire
- Add optional birth time support with a clearly disclosed `00:00` fallback.
- Add a chart-informed questionnaire using plain personality language and 1–5 ratings.
- Generate early profile traits from astrology engine.
- Return interpretation previews with confidence tags.
- Add endpoint for validation answer submission.

### Weeks 5–6: Analysis flow and LLM interpretation
- Implement LLM integration with configurable endpoint/model.
- Add constrained prompt schema for safety and reproducibility.
- Add a focused analysis flow:
  - guest personality preview,
  - editable username recommendations,
  - Google login gate for the complete analysis,
  - natal-chart detail after login,
  - feedback capture.
- Add admin provider settings and prompt audit history.

### Weeks 7–8: Public alpha
- Add mobile-first responsive polish.
- Run a smoke usability test (minimum 5 participants).
- Complete OSS documentation:
  - API contract,
  - deployment notes,
  - contribution guide.
- Release **Open Source Alpha**.

## Post-alpha scope

- Stronger timezone fallback and auto-correction for birth place variants.
- Production deployment for `hermex.fun`.
- Long-term progress journal feature.
- Exportable insight report (optional).

## Success criteria for MVP

- User can submit place + birth date with an optional birth time.
- Questionnaire uses 1–5 ratings and never exposes astrology terms.
- User receives:
  1) a guest preview,
  2) editable username recommendations,
  3) a complete analysis after Google login.
- Main page and card render under 2.5 seconds on average connection.
- Documentation remains complete and understandable.

## Risks and mitigations

- **Deterministic astrology interpretation risk**
  - Show strong non-deterministic disclaimers.
  - Keep AI outputs as guidance with confidence labels.
- **Location/time precision risk**
  - Always validate timezone and allow manual override.
- **Flow complexity risk**
  - Keep the analysis steps simple for alpha.
  - Add only changes that improve completion or clarity.

## Naming policy

- Working name remains **Hermex**.
- Repository name remains `hermex`.
- Hermes theme remains in copy and storyline only.
