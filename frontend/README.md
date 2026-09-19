# crowdLens frontend

React + TypeScript + Vite dashboard. Follows `DESIGN-SYSTEM.md` — the visual
language derived from the CRM analytics reference: Inter, near-white canvas,
borderless rounded cards, black pill controls, one rationed lime accent, and
risk-band colors confined to band indicators.

## Run

The backend must be running on :8000 first (see `../backend/README.md`). Then:

```bash
npm install
npm run dev
```

Opens on http://localhost:5173 and proxies `/v1/*` to the backend.

### No backend? Click **▶ Demo**

The top bar has a **Demo** button that loads a full hardcoded report — every
card populated with the "beef bar" case, including varied persona reactions,
the emotion spread, the backlash pathway, blind spots, and three re-scored
rewrites. It needs no backend and no Claude credential, so the dashboard can be
shown standalone.

## Structure

- `src/App.tsx` — shell, composer, and the eight-question analysis layout
- `src/panels/panels.tsx` — the metric panels (intent, emotion, risk, who)
- `src/panels/special.tsx` — trigger highlighting, backlash pathway, blind
  spots, rewrites
- `src/components/ui.tsx` — Card, Chip, ScoreGauge, Meter primitives
- `src/lib/api.ts` — typed client mirroring the backend's report shape
- `src/styles/tokens.css` — design tokens from DESIGN-SYSTEM.md

## Honesty requirements (from DESIGN-SYSTEM.md §7.4)

Enforced in the UI, not optional polish:

- The score is a **Risk Index**, never a probability.
- The confidence interval is **always drawn as a band**, never collapsed.
- A wide interval triggers the "audience is split" callout.
- Tier-2 blind-spot findings are **visually quarantined**: the only dashed,
  bordered cards in the system, each carrying a persistent NOT SCORED tag.
- The context provenance badge is always visible.
