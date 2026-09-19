# crowdLens backend

API-only backlash simulation engine. No frontend — everything is exposed over HTTP.

## Authentication

crowdLens authenticates to Claude using your **existing Claude credentials**. No API key needs to live in a `.env` file.

```bash
claude setup-token
export CLAUDE_CODE_OAUTH_TOKEN='<the token it prints>'
```

Resolution order is `CLAUDE_CODE_OAUTH_TOKEN` → `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY`. If none resolve, the server refuses to start and prints setup instructions rather than failing later with an opaque 401.

> **Deployment note.** A subscription OAuth token is tied to one Claude account and is not licensed for serving other people's traffic. It is the right credential for local development. A multi-user deployment needs its own `ANTHROPIC_API_KEY`.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Interactive API docs at http://localhost:8000/docs

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/health` | Status, auth kind, persona count, scenarios |
| `POST` | `/v1/simulate` | Run a simulation — the one expensive call |
| `GET` | `/v1/runs` | Recent runs |
| `GET` | `/v1/runs/{id}` | Full report |
| `GET` | `/v1/runs/{id}/panels/{panel}` | One panel, no re-simulation |
| `GET` | `/v1/panels` | Available panel names |
| `GET` | `/v1/personas` | Persona registry |
| `GET` | `/v1/personas/{id}` | One persona definition |
| `POST` | `/v1/personas/reload` | Reload YAML without restarting |
| `GET` | `/v1/scenarios` | Context fixtures |

### Example

```bash
curl -X POST localhost:8000/v1/simulate -H 'content-type: application/json' -d '{
  "copy": "Our new protein bar — finally, a beef bar that doesn'\''t taste like a cow.",
  "brand_intent": "Position our protein bar as great-tasting and high-protein.",
  "context_scenario": "dietary_controversy_india"
}'
```

## Architecture

```
POST /v1/simulate
    │
    ├─ triage (Haiku)          extract activated sensitivity axes
    ├─ router  N→K             axis match + MMR diversity + adversarial slots
    ├─ Tier 1 fan-out          K persona reactions, parallel  ──┐
    ├─ Tier 2 composition      EIG-selected intersections     ──┤ concurrent
    └─ aggregation             score, CI, 20+ panel projections ┘
```

**The score comes from Tier 1 only.** Tier-2 composites are correlated with their parents by construction; including them would narrow the confidence interval through redundancy rather than evidence. `compute_score` raises on tier-2 input — the constraint is structural, not a convention.

### Key modules

| Path | Role |
|---|---|
| `app/personas/schema.py` | The Reaction Object — 14 panels are projections over it |
| `app/scoring/model.py` | Risk index: offense mass, amplification, tail risk, ambiguity |
| `app/scoring/uncertainty.py` | Bootstrap + jackknife interval |
| `app/router/select.py` | N→K selection |
| `app/analysis/projections.py` | The free panels |
| `app/composition/compose.py` | Tier 2 |
| `app/context/provider.py` | κ context multiplier (mock fixtures) |

## Tests

```bash
.venv/bin/python -m pytest tests/unit -q
```

25 tests. The load-bearing ones:

- `test_tail_risk_survives_averaging` — eleven personas at 0.1 and one at 1.0 is a campaign on fire, not a 0.175
- `test_composites_rejected_from_scoring` — tier enforcement
- `test_composites_would_narrow_the_interval` — executable argument for the two-tier split
- `test_interval_never_claims_certainty` — a small panel cannot justify a point estimate
- `test_control_node_excluded_from_score` — the canary must not vote on the score it monitors

## Status

**Stage 1 of 4.** Working: persona registry, selection, fan-out, scoring, uncertainty, composition, 20+ panels, mock context.

Not yet built: rewrite engine (stage 2), interpretation clustering and embeddings (stage 3), historical corpus and comparison panels (stage 4), live context providers, persistence.

Scoring weights in `app/config.py` are **priors to be calibrated against a golden set, not validated constants**. Model pricing in `app/llm/client.py` is indicative — verify against current Anthropic documentation.
