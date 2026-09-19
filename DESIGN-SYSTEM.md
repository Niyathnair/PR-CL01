# crowdLens — Design System

**Visual language derived from:** *Modern CRM & Analytics Platform SaaS & UX UI Design*, Gulshan Ali & Ibdai (Behance, published 2025-10-20). Source PDF in repo root.

**Status:** Specification. No frontend is built yet — this document defines the language for when one is.

---

## 1. The Language in One Paragraph

A near-white canvas carrying softly rounded, borderless cards that separate by **elevation and tone rather than by lines**. Typography is Inter, set large and light, with headings that dominate by size rather than weight. One acid-lime accent does all the emphasis work — nothing else competes. Controls are black pills and circular icon buttons. Charts are restrained: hairline strokes, hatch fills, a single lime marker on the one value that matters. The result reads as calm, data-dense, and expensive.

**The discipline that makes it work:** the accent is rationed. A screen has one or two lime elements, never five. Remove that restraint and the whole system collapses into a generic dashboard.

---

## 2. Color

### 2.1 Core palette (exact, from the source's own swatch page)

| Token | Hex | Role |
|---|---|---|
| `--ink` | `#000000` | Text, primary buttons, focused states |
| `--paper` | `#FFFFFF` | Card surfaces |
| `--lime` | `#C7F33C` | The accent. Rationed. |
| `--lime-pale` | `#E1F2AE` | Lime at low emphasis — secondary fills, chart bands |

### 2.2 Derived neutrals

The source works almost entirely in the range between white and a light warm grey. These fill it out:

| Token | Hex | Role |
|---|---|---|
| `--canvas` | `#EFEFEF` | App background, behind cards |
| `--surface` | `#F7F7F7` | Card fill on canvas (the default card) |
| `--surface-raised` | `#FFFFFF` | Cards that need to sit above others |
| `--hairline` | `#E4E4E4` | Chart axes, dividers — used sparingly |
| `--text-primary` | `#000000` | Headings, values |
| `--text-secondary` | `#6B6B6B` | Labels, captions, axis text |
| `--text-tertiary` | `#A0A0A0` | Disabled, placeholder |

### 2.3 Dark mode

The source has no dark variant. Rather than invent a dark palette and claim it came from the reference, these are **crowdLens extensions** — an inversion that keeps lime's relationship to its background intact:

| Token | Light | Dark |
|---|---|---|
| `--canvas` | `#EFEFEF` | `#0D0D0D` |
| `--surface` | `#F7F7F7` | `#1A1A1A` |
| `--surface-raised` | `#FFFFFF` | `#242424` |
| `--text-primary` | `#000000` | `#F5F5F5` |
| `--text-secondary` | `#6B6B6B` | `#9A9A9A` |
| `--hairline` | `#E4E4E4` | `#2E2E2E` |
| `--lime` | `#C7F33C` | `#C7F33C` |
| `--lime-pale` | `#E1F2AE` | `#3D4A1C` |

Lime is unchanged — it reads correctly on both. Note that **lime requires black text on top in both themes**; white on lime fails contrast badly.

### 2.4 Risk bands — where this system must diverge from its source

The source uses lime decoratively: whichever card is featured gets it. crowdLens cannot do that, because **color has to carry meaning here.** A five-band risk scale rendered in one accent tells the user nothing.

So: lime keeps its visual role but takes on a semantic one, and four risk colors are introduced as a **deliberate, documented extension**.

| Band | Token | Hex | Reasoning |
|---|---|---|---|
| Clear | `--band-clear` | `#C7F33C` | The source lime. Clear is the good outcome, and lime is the system's positive accent. |
| Low | `--band-low` | `#E1F2AE` | Pale lime — the same family, dialed down. |
| Elevated | `--band-elevated` | `#F5C518` | Amber. Departs from the palette because the user must see a step change. |
| High | `--band-high` | `#F07A2B` | Orange. |
| Severe | `--band-severe` | `#D93636` | Red. |

Three rules keep this from polluting the palette:

1. **Band colors appear only on band indicators** — the score gauge, band chips, and the severity axis of the risk matrix. Never as decoration, never as a card fill.
2. **Every band chip carries its label as text.** Color reinforces; text carries. This is not optional — ~8% of men have some form of color vision deficiency, and a red/orange distinction is exactly what they lose.
3. **Amber, orange and red do not appear anywhere else in the product.** Seeing them means risk, always.

### 2.5 Categorical colors for charts

Persona and emotion charts need distinguishable series. Lime plus greys will not carry seven categories.

```
--cat-1: #2E2E2E   (near-black)
--cat-2: #C7F33C   (lime)
--cat-3: #7A8B99   (slate)
--cat-4: #E1F2AE   (pale lime)
--cat-5: #B5A88F   (warm taupe)
--cat-6: #5C6670   (deep slate)
--cat-7: #D6D6D6   (light grey)
```

Ordered so that the first three are maximally separable — most charts use three or fewer. Emotion charts should map the seven emotions to a **diverging** arrangement (positive → lime end, offended → dark end) rather than these categoricals, since emotion is ordered, not nominal.

---

## 3. Typography

**Inter.** Confirmed on the source's type page, with its own scale:

| Role | Size | Weight | Tracking |
|---|---|---|---|
| Heading | 34px | 300 Light | −0.02em |
| Title | 28px | 400 Regular | −0.01em |
| Body | 16px | 400 Regular | 0 |

Extended for a data product (the source lists "+9 styles" without showing them):

| Role | Size | Weight | Use |
|---|---|---|---|
| Display | 56px | 300 | The Risk Index number |
| Heading | 34px | 300 | Page titles |
| Title | 28px | 400 | Card titles |
| Subtitle | 20px | 500 | Section headers |
| Body | 16px | 400 | Default |
| Body-sm | 14px | 400 | Dense tables, persona cards |
| Label | 13px | 500 | Field labels, chips |
| Caption | 12px | 400 | Axis text, timestamps |

### 3.1 The rule that defines this look

**Large text is light; small text is not.** Headings at 300 weight, body at 400, labels at 500. Inverting this — bold headings — produces a completely different, much heavier product. The source's authority comes from *size*, not weight.

Metric values (`$29,48m`, `52`) are set at Display or Heading size in **300 weight**, with the unit suffix at 40% of the number's size in `--text-secondary`.

Numerals use `font-variant-numeric: tabular-nums` everywhere a value updates or aligns in a column, so digits do not jitter.

---

## 4. Shape and Elevation

### 4.1 Radii

Generous throughout. Nothing in the source has a sharp corner.

```
--radius-card:   24px    cards, panels
--radius-inner:  16px    elements nested inside cards
--radius-input:  12px    fields
--radius-pill:   999px   buttons, chips, tabs, badges
```

### 4.2 Elevation

Cards separate by **tone and shadow, not borders.** A 1px grey border anywhere on a card is a deviation from this system.

```
--shadow-flat:    none
--shadow-card:    0 1px 2px rgba(0,0,0,.04), 0 4px 12px rgba(0,0,0,.04)
--shadow-raised:  0 2px 4px rgba(0,0,0,.06), 0 12px 32px rgba(0,0,0,.08)
--shadow-overlay: 0 8px 16px rgba(0,0,0,.08), 0 24px 64px rgba(0,0,0,.12)
```

Shadows are wide and very soft — large blur, low opacity. A tight dark shadow reads as cheap here.

### 4.3 Spacing

8px base:

```
4 · 8 · 12 · 16 · 24 · 32 · 48 · 64
```

Card padding: 24px desktop, 16px mobile. Gap between cards: 16px. Page gutter: 32px desktop, 16px mobile.

---

## 5. Components

### 5.1 Card

The fundamental unit. `--surface` fill, `--radius-card`, `--shadow-card`, 24px padding, **no border**.

Header pattern seen consistently in the source: title at top-left in Title size, circular icon buttons at top-right (36px, `--surface-raised` fill, no border). One card per screen may use `--surface-raised` to pull forward.

An **inverted card** — `--ink` fill, white text — is used for exactly one metric per screen (the source does this with "Today revenue"). This is the strongest emphasis available. Use it at most once per view.

### 5.2 Button

| Variant | Fill | Text | Use |
|---|---|---|---|
| Primary | `--ink` | white | The one main action |
| Accent | `--lime` | `--ink` | Positive confirmation (accept a rewrite) |
| Secondary | `--surface-raised` | `--ink` | Everything else |
| Ghost | transparent | `--text-secondary` | Tertiary |

All pill-shaped. Height 40px standard, 32px compact. Padding 20px horizontal. Icon-only buttons are perfect circles.

### 5.3 Tab bar

A pill-shaped container in `--surface`, with the active tab as a solid `--ink` pill and inactive tabs as plain text in `--text-secondary`. This is the source's primary navigation pattern and should be crowdLens's too — it suits the eight-question structure directly.

### 5.4 Chip / Badge

Pill, 24–28px tall, Label type. Neutral chips take `--surface-raised`; the accent chip takes `--lime` with black text — used for the single most important value on a chart, exactly as the source marks `+9%` on its revenue line.

### 5.5 Data display

Charts follow the source's restraint:

- **Line charts**: 1.5px stroke in `--ink`. Comparison series use a **diagonal hatch fill** rather than a second color — distinctive and prints well.
- **Bar charts**: `--surface-raised` bars with `--radius-inner`, the highlighted bar in `--lime`.
- **Axes**: no gridlines. Labels only, in Caption size, `--text-secondary`.
- **Highlight marker**: one lime pill with the value, on the single point that matters.
- **Heatmaps**: the source uses a lime-saturation grid. Use `--lime-pale` → `--lime` → `--ink` for sequential intensity.

**Never more than one lime element per chart.** If two things are important, the chart is doing too much.

---

## 6. Applying This to crowdLens

### 6.1 The Risk Index

Display 56px/300, tabular numerals. Band label as a chip beneath it, in that band's color with the name as text.

**The confidence interval is drawn as a band, never hidden.** This is a product requirement (plan §17.3), not a style choice: a point estimate alone implies precision the method does not have. Render it as a horizontal track with the interval as a filled region and the point as a marker.

A wide interval triggers a callout chip — *"Your audience is split on this"* — at Label size, in amber. Wide disagreement must be as visible as a high score.

### 6.2 Intent Alignment Score

Sits **beside** the Risk Index at equal visual weight, never beneath it. A campaign can be perfectly safe and still fail to communicate; a layout that subordinates IAS teaches users that risk is the only thing that matters.

### 6.3 Persona reaction cards

Standard cards, `--surface`. Emotion as a chip; severity as a small bar. The reaction quote is the hero — **Body size, not Caption**, in `--text-primary`. First-person voice is what makes this land emotionally, and shrinking it to caption size wastes the product's best asset.

### 6.4 Trigger highlighting

Inline spans in the copy get a `--lime-pale` background at `--radius-input`, escalating to `--lime` for the highest-severity span. Hovering reveals the personas it triggered.

Severity is shown by **underline weight** (1px → 3px) in addition to fill, so the signal survives for a user who cannot distinguish the two lime tones.

### 6.5 Blind Spot Findings — visual quarantine

Tier-2 composite findings must be **unmistakably separated** from measured results (plan §7.2, §17.3). They are model interpolations without ground truth, and they are the most fluent-sounding output the system produces — which is exactly what makes mislabeling them dangerous.

The treatment:

- A distinct card style: `--canvas` fill with a **2px dashed `--hairline` border** — the only dashed border in the entire system, and the only card with a border at all.
- A persistent `NOT SCORED` chip in `--text-secondary`, always visible, never behind a hover or a collapse.
- One-click dismiss, always present.
- No band color, no risk gauge, no number that could be mistaken for a measurement.

A user who cannot tell a blind-spot finding from a scored result at a glance means this has failed. Test it on someone who has not read the plan.

### 6.6 Severe Discovery Alert

A modal in `--surface-raised` with `--shadow-overlay`. It uses `--band-severe` for its icon only — **not** for the Risk Index, which does not move. The copy must state plainly that the score is unchanged, because the alert's prominence otherwise implies it did.

---

## 7. Motion

Restrained. The source is still imagery, so this is a crowdLens extension in the spirit of it.

```
--ease:        cubic-bezier(0.4, 0, 0.2, 1)
--duration-sm: 150ms   hover, focus
--duration-md: 250ms   card expand, tab switch
--duration-lg: 400ms   panel transitions
```

Persona reactions **stream in as they return** rather than appearing all at once — this matters more for perceived quality than almost anything else in the UI, and it suits a system where results genuinely arrive incrementally.

All motion respects `prefers-reduced-motion: reduce`.

---

## 8. Accessibility

Two places where this palette is actively risky, both called out because they are easy to get wrong:

1. **Lime on white fails contrast.** `#C7F33C` on `#FFFFFF` is ~1.4:1. Lime is a *fill* behind black text, never a text color on a light background, and never a lone carrier of meaning.
2. **Band colors need redundant encoding.** Every band chip carries its name as text. Every chart series distinguishable by color is also distinguishable by position, pattern, or direct label.

Other requirements: focus rings are a 2px `--ink` outline with 2px offset (visible on every surface in the palette); hit targets ≥44px; body text never below 14px; `--text-secondary` on `--surface` is 5.4:1, which passes, while `--text-tertiary` is decorative only and never carries information.

---

## 9. CSS Tokens

```css
:root {
  --canvas: #EFEFEF;
  --surface: #F7F7F7;
  --surface-raised: #FFFFFF;
  --ink: #000000;
  --hairline: #E4E4E4;

  --lime: #C7F33C;
  --lime-pale: #E1F2AE;

  --text-primary: #000000;
  --text-secondary: #6B6B6B;
  --text-tertiary: #A0A0A0;

  --band-clear: #C7F33C;
  --band-low: #E1F2AE;
  --band-elevated: #F5C518;
  --band-high: #F07A2B;
  --band-severe: #D93636;

  --cat-1: #2E2E2E; --cat-2: #C7F33C; --cat-3: #7A8B99; --cat-4: #E1F2AE;
  --cat-5: #B5A88F; --cat-6: #5C6670; --cat-7: #D6D6D6;

  --radius-card: 24px;
  --radius-inner: 16px;
  --radius-input: 12px;
  --radius-pill: 999px;

  --shadow-card: 0 1px 2px rgba(0,0,0,.04), 0 4px 12px rgba(0,0,0,.04);
  --shadow-raised: 0 2px 4px rgba(0,0,0,.06), 0 12px 32px rgba(0,0,0,.08);
  --shadow-overlay: 0 8px 16px rgba(0,0,0,.08), 0 24px 64px rgba(0,0,0,.12);

  --font: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
}

:root:not([data-theme="light"]) {
  @media (prefers-color-scheme: dark) {
    --canvas: #0D0D0D;
    --surface: #1A1A1A;
    --surface-raised: #242424;
    --hairline: #2E2E2E;
    --text-primary: #F5F5F5;
    --text-secondary: #9A9A9A;
    --text-tertiary: #6E6E6E;
    --lime-pale: #3D4A1C;
  }
}

:root[data-theme="dark"] {
  --canvas: #0D0D0D;
  --surface: #1A1A1A;
  --surface-raised: #242424;
  --hairline: #2E2E2E;
  --text-primary: #F5F5F5;
  --text-secondary: #9A9A9A;
  --text-tertiary: #6E6E6E;
  --lime-pale: #3D4A1C;
}

body {
  background: var(--canvas);
  color: var(--text-primary);
  font-family: var(--font);
  font-size: 16px;
  line-height: 1.5;
}
```

---

## 10. What Came From Where

Honest provenance, so nobody later mistakes an extension for a source requirement:

**From the reference:** exact palette (#000000, #FFFFFF, #C7F33C, #E1F2AE) · Inter · the 34/28/16 scale · light-weight large headings · borderless rounded cards on a near-white canvas · black pill buttons and circular icon buttons · pill tab bar with solid active state · hatch-fill comparison charts · single lime highlight marker · one inverted black metric card per screen.

**crowdLens extensions, not in the source:** dark mode · the derived neutral ramp · risk band colors (amber/orange/red) · categorical chart colors · motion tokens · the extended type scale beyond three sizes · the dashed-border treatment for Tier-2 findings · accessibility requirements.

The extensions exist because crowdLens is a risk product and the source is a sales CRM. Where the two conflict — most sharply on whether color may be decorative — **meaning wins**, and the deviation is documented rather than silent.

---

*Derived 2026-09-19 from the source PDF in this repository. Where this document and the plan's §17.3 honesty requirements disagree, §17.3 governs: a visual choice that makes a simulated number look more certain than it is, is wrong regardless of how well it matches the reference.*
