# Hermex Open Source Development Plan

This plan is optimized for a small team or solo maintainer.

## Vision

Build a lightweight, fun web game for self-discovery with clear natal chart inputs and practical, confidence-aware career insights.

## MVP target (8 weeks)

### Weeks 1–2: Foundation
- Initialize FE + BE monorepo.
- Configure baseline CI for lint/tests.
- Implement `POST /api/v1/birth/analyze`.
- Create birth input UI and basic validation.
- Persist profiles and sessions in SQLite.

### Weeks 3–4: Birth + Questionnaire
- Add optional name handling and optional birth time support.
- Add validation questionnaire flow for missing or uncertain details.
- Generate early profile traits from astrology engine.
- Return interpretation previews with confidence tags.
- Add endpoint for validation answer submission.

### Weeks 5–6: Gameplay and LLM interpretation
- Implement LLM integration with configurable endpoint/model.
- Add constrained prompt schema for safety and reproducibility.
- Add initial native-app style quest UI:
  - natal chart explorer,
  - Hermes AI interpretation,
  - minat/bakat cards,
  - last-5-year roadmap,
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
- Jodoh Similarity for comparing two charts.
- Long-term progress journal feature.
- Anonymous community leaderboard.
- Exportable insight report (optional).

## Success criteria for MVP

- User can submit place + birth date (name optional, time optional).
- Questionnaire flow runs when needed and increases confidence score.
- User receives:
  1) interest profile,
  2) talent profile,
  3) 2+ career roadmaps with confidence labels.
- Main page and card render under 2.5 seconds on average connection.
- Documentation remains complete and understandable.

## Risks and mitigations

- **Deterministic astrology interpretation risk**
  - Show strong non-deterministic disclaimers.
  - Keep AI outputs as guidance with confidence labels.
- **Location/time precision risk**
  - Always validate timezone and allow manual override.
- **Gameplay complexity risk**
  - Keep mechanics simple for alpha.
  - Add only small, meaningful expansions.

## Naming policy

- Working name remains **Hermex**.
- Repository name remains `hermex`.
- Hermes theme remains in copy and storyline only.
