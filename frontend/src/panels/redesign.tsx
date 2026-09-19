/* Panels for the four-band redesign: L1 strip, feel+word-cloud, campaign
   highlight+rewrites, persona illustrations, India map, target Venn, comparison,
   risk anatomy. */

import type { Report } from "../lib/api";
import { BAND_COLOR, type Band } from "../lib/api";
import { Card, Chip, BandChip, Empty, emotionColor } from "../components/ui";
import { INDIA_PATHS, INDIA_VB } from "../lib/indiaMap";

/* ── Band 1: five L1 metrics across the top ── */
export function L1Strip({ report }: { report: Report }) {
  return (
    <div className="l1strip">
      {report.l1_metrics.map((m) => {
        const inverted = m.tone === "inverted";
        return (
          <div key={m.key} className={`l1 ${inverted ? "l1--inverted" : ""}`}>
            <div className="l1__label">{m.label}</div>
            <div className="l1__value tabular">
              {m.value}
              {m.unit && <span className="l1__unit">{m.unit}</span>}
            </div>
            {m.tone === "band" ? (
              <BandChip band={report.risk_index.band} />
            ) : (
              <div className="l1__sub">{m.sub}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Band 2 left-upper: How do they feel — stacked segment bar with axis,
   in the style of the reference image (proportional horizontal segments). ── */
export function FeelChart({ report }: { report: Report }) {
  const er = report.feeling.emotional_response;
  const entries = Object.entries(er.distribution).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
  // Axis ticks at 0 / 50 / 100 % of the audience.
  return (
    <Card title="How do they feel?">
      <div className="segbar">
        {entries.map(([e, v]) => (
          <div
            key={e}
            className="segbar__seg"
            style={{ width: `${(v / total) * 100}%`, background: emotionColor(e) }}
            title={`${e}: ${(v * 100).toFixed(0)}%`}
          >
            {v / total > 0.08 && <span className="segbar__lbl">{e}</span>}
          </div>
        ))}
      </div>
      <div className="segbar__axis tabular">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
      </div>
      <div className="segbar__legend">
        {entries.map(([e, v]) => (
          <span key={e} className="segbar__key">
            <span className="segbar__dot" style={{ background: emotionColor(e) }} />
            {e} <span className="tabular mut">{(v * 100).toFixed(0)}%</span>
          </span>
        ))}
      </div>
      {er.polarization > 0.3 && (
        <div className="split-note">⚡ Polarization {(er.polarization * 100).toFixed(0)}% — strong love and strong hate.</div>
      )}
    </Card>
  );
}

/* ── Band 2 left-lower: "What they're saying" as a TREEMAP.
   Boxes sized by how many react that way, tinted on a red→green scale with the
   most-negative reaction the biggest/reddest, the most-positive smallest/green,
   with the comment text inside each box. ── */

// Squarified-ish treemap: simple slice-and-dice that alternates split direction,
// good enough for ~8-12 boxes and keeps boxes readable.
interface TNode { text: string; weight: number; sentiment: string; label: string; tone: number }
function layoutTreemap(items: TNode[], x: number, y: number, w: number, h: number, horizontal: boolean): Array<TNode & { x: number; y: number; w: number; h: number }> {
  if (items.length === 0) return [];
  if (items.length === 1) return [{ ...items[0], x, y, w, h }];
  const total = items.reduce((s, i) => s + i.weight, 0) || 1;
  // Split items into two halves of roughly equal weight.
  let acc = 0, idx = 0;
  for (let i = 0; i < items.length; i++) { acc += items[i].weight; if (acc >= total / 2) { idx = i + 1; break; } }
  idx = Math.max(1, Math.min(items.length - 1, idx));
  const a = items.slice(0, idx), b = items.slice(idx);
  const aw = a.reduce((s, i) => s + i.weight, 0) / total;
  if (horizontal) {
    const wa = w * aw;
    return [...layoutTreemap(a, x, y, wa, h, false), ...layoutTreemap(b, x + wa, y, w - wa, h, false)];
  } else {
    const ha = h * aw;
    return [...layoutTreemap(a, x, y, w, ha, true), ...layoutTreemap(b, x, y + ha, w, h - ha, true)];
  }
}

// Red (bad) → green (good) tint from a signed tone in [-1, 1].
function toneColor(tone: number): string {
  if (tone > 0.15) return "var(--band-clear)"; // favourable → green
  if (tone < -0.5) return "var(--band-severe)"; // strongly negative → red
  if (tone < -0.15) return "var(--band-high)"; // negative → orange-red
  return "var(--cat-7)"; // neutral → grey
}

export function CommentCloud({ report }: { report: Report }) {
  const cs = report.feeling.simulated_comments;
  const reactions = report.feeling.persona_reactions;
  const sentOf: Record<string, string> = {};
  const sevOf: Record<string, number> = {};
  for (const r of reactions) { sentOf[r.persona_id] = r.sentiment; sevOf[r.persona_id] = r.severity; }

  const nodes: TNode[] = cs.map((c) => {
    const sent = sentOf[c.persona_id] || "indifferent";
    const sev = sevOf[c.persona_id] ?? 0.2;
    // tone: negative sentiment pushes toward red (scaled by severity), favourable toward green.
    const tone = sent === "opposed" ? -sev : sent === "favorable" ? 0.6 : -0.05;
    return { text: c.text, weight: Math.max(c.weight, 0.02), sentiment: sent, label: c.label, tone };
  });
  // Biggest + reddest first: sort by weight desc so the layout places large boxes first.
  nodes.sort((a, b) => b.weight - a.weight);
  const boxes = layoutTreemap(nodes, 0, 0, 100, 100, true);

  return (
    <Card title="What they're saying">
      <div className="treemap">
        {boxes.map((box, i) => (
          <div
            key={i}
            className="tm-box"
            style={{
              left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%`,
              background: toneColor(box.tone),
            }}
            title={`${box.label}`}
          >
            <span className="tm-text" style={{ fontSize: `${Math.min(15, 8 + box.w * 0.08 + box.h * 0.04)}px` }}>
              "{box.text}"
            </span>
          </div>
        ))}
      </div>
      <div className="tiny mut" style={{ marginTop: 8 }}>Box size = how many react that way. Red = negative, green = positive.</div>
    </Card>
  );
}

/* ── Band 2 right: campaign copy highlighted + rewrites ── */
export function CampaignHighlight({ report, onRewrite }: { report: Report; onRewrite: () => void }) {
  const copy = report.copy;
  const spans = [...report.cause.trigger_index].sort((a, b) => a.char_start - b.char_start);
  const segs: { text: string; trig?: (typeof spans)[0] }[] = [];
  let cursor = 0;
  for (const s of spans) {
    if (s.char_start < cursor) continue;
    if (s.char_start > cursor) segs.push({ text: copy.slice(cursor, s.char_start) });
    segs.push({ text: copy.slice(s.char_start, s.char_end), trig: s });
    cursor = s.char_end;
  }
  if (cursor < copy.length) segs.push({ text: copy.slice(cursor) });

  return (
    <Card title="What could be felt as offensive">
      <div className="hl-copy">
        {segs.map((s, i) =>
          s.trig ? (
            <span key={i} className="hl-red" tabIndex={0}>
              {s.text}
              <span className="hl-pop">
                <strong>{s.trig.persona_count} personas flagged "{s.trig.span}"</strong>
                <div>{s.trig.personas[0]?.why}</div>
                <div className="tiny mut">max severity {(s.trig.max_severity * 100).toFixed(0)} · {(s.trig.audience_mass * 100).toFixed(0)}% of audience</div>
              </span>
            </span>
          ) : (
            <span key={i}>{s.text}</span>
          )
        )}
      </div>
      <div className="row" style={{ marginTop: 16, justifyContent: "space-between" }}>
        <span className="tiny mut">Hover a red span for why it's risky.</span>
        <button className="btn btn--accent" onClick={onRewrite}>✏️ See rewrites</button>
      </div>
    </Card>
  );
}

/* ── Band 3: persona illustrations, positive left / negative right ──
   Faces are the supplied person SVGs, assigned deterministically per persona. */

// Stable string hash → 1..28 face index.
function faceFor(id: string): string {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  const n = (h % 28) + 1;
  return `/faces/person_${String(n).padStart(2, "0")}.svg`;
}

function PersonaFace({ p }: { p: Report["feeling"]["persona_reactions"][0] }) {
  const positive = p.sentiment === "favorable";
  const negative = p.sentiment === "opposed";
  const feeling = negative ? "offended" : positive ? "likes it" : "neutral";
  const pct = Math.round(p.severity * 100);
  const short = p.label.length > 28 ? p.label.slice(0, 28) + "…" : p.label;
  const ring = negative ? "var(--band-high)" : positive ? "var(--band-clear)" : "var(--cat-7)";
  return (
    <div className="face" tabIndex={0}>
      <div className="face__top">
        <span className="face__feel" style={{ color: negative ? "var(--band-high)" : positive ? "var(--band-clear)" : "var(--text-secondary)" }}>
          {feeling} {negative || positive ? `${pct}%` : ""}
        </span>
      </div>
      <div className="face__img" style={{ borderColor: ring }}>
        <img src={faceFor(p.persona_id)} alt={p.label} loading="lazy" />
      </div>
      <div className="face__demo">{short}</div>
      <div className="face__pop">
        <strong>{p.label}</strong>
        <div className="tiny mut" style={{ margin: "4px 0" }}>{p.emotion} · severity {pct} · {p.comprehension}</div>
        <div>"{p.likely_comment.text}"</div>
      </div>
    </div>
  );
}

export function PersonaBoards({ report }: { report: Report }) {
  const rs = report.feeling.persona_reactions;
  const positive = rs.filter((p) => p.sentiment === "favorable").sort((a, b) => a.severity - b.severity).slice(0, 3);
  const negative = rs.filter((p) => p.sentiment === "opposed").sort((a, b) => b.severity - a.severity).slice(0, 3);
  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <Card title="Top personas reacting positively">
        <div className="faces">{positive.length ? positive.map((p) => <PersonaFace key={p.persona_id} p={p} />) : <Empty>None reacting positively.</Empty>}</div>
      </Card>
      <Card title="Top personas reacting negatively">
        <div className="faces">{negative.length ? negative.map((p) => <PersonaFace key={p.persona_id} p={p} />) : <Empty>None reacting negatively.</Empty>}</div>
      </Card>
    </div>
  );
}

/* ── Band 4a: India region heatmap — the real India SVG, states tinted by
   signed intensity (red = offended, green = favourable). ── */
export function IndiaHeatmap({ report }: { report: Report }) {
  const geo = report.geo_india;
  // Map "MH" -> intensity, keyed the way the SVG ids are ("IN-MH").
  const byId: Record<string, { intensity: number; name: string }> = {};
  for (const s of geo.states) byId[`IN-${s.code}`] = { intensity: s.intensity, name: s.name };

  const fill = (t: number | undefined) => {
    if (t === undefined) return "var(--surface-raised)";
    if (t > 0.5) return "var(--band-severe)";
    if (t > 0.15) return "var(--band-high)";
    if (t < -0.15) return "var(--band-clear)";
    return "var(--cat-7)";
  };

  return (
    <Card title="India — regional response">
      {!geo.available ? (
        <Empty>No India regional signal.</Empty>
      ) : (
        <>
          <svg viewBox={INDIA_VB} className="india-map" preserveAspectRatio="xMidYMid meet">
            {INDIA_PATHS.map((st) => {
              const hit = byId[st.id];
              return (
                <path
                  key={st.id}
                  d={st.d}
                  fill={fill(hit?.intensity)}
                  fillOpacity={hit ? 0.4 + Math.abs(hit.intensity) * 0.55 : 1}
                  stroke="var(--hairline)"
                  strokeWidth="0.7"
                >
                  <title>
                    {st.title}
                    {hit ? `: ${hit.intensity > 0 ? "offended" : "favourable"} ${Math.abs(hit.intensity * 100).toFixed(0)}%` : ""}
                  </title>
                </path>
              );
            })}
          </svg>
          <div className="row" style={{ gap: 12, marginTop: 8, justifyContent: "center" }}>
            <Chip><span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--band-severe)", display: "inline-block" }} /> offended</Chip>
            <Chip><span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--band-clear)", display: "inline-block" }} /> favourable</Chip>
          </div>
        </>
      )}
    </Card>
  );
}

/* ── Band 4b: target-audience Venn ── */
export function TargetVenn({ report }: { report: Report }) {
  const v = report.target_venn;
  if (!v.available || !v.buckets) return <Card title="Target audience"><Empty>{v.reason || "Set a target age to see the Venn."}</Empty></Card>;
  const b = v.buckets;
  const pct = (k: string) => ((b[k] || 0) * 100).toFixed(0);
  return (
    <Card title={`Target audience (${v.target_age?.[0]}–${v.target_age?.[1]})`}>
      <svg viewBox="0 0 200 140" className="venn">
        {/* Target circle (center), positive overlap (left), negative overlap (right) */}
        <circle cx="100" cy="70" r="52" fill="var(--lime-pale)" fillOpacity="0.5" stroke="var(--ink)" strokeWidth="1" />
        <circle cx="62" cy="70" r="42" fill="var(--band-clear)" fillOpacity="0.35" stroke="var(--band-clear)" strokeWidth="1" />
        <circle cx="138" cy="70" r="42" fill="var(--band-high)" fillOpacity="0.3" stroke="var(--band-high)" strokeWidth="1" />
        <text x="100" y="66" textAnchor="middle" fontSize="9" fill="var(--text-secondary)">Target</text>
        <text x="100" y="78" textAnchor="middle" fontSize="11" fontWeight="600" className="tabular">{pct("target_neutral")}%</text>
        <text x="44" y="70" textAnchor="middle" fontSize="10" fontWeight="600" className="tabular">{pct("target_positive")}%</text>
        <text x="156" y="70" textAnchor="middle" fontSize="10" fontWeight="600" className="tabular">{pct("target_negative")}%</text>
      </svg>
      <div className="row" style={{ gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
        <Chip color="var(--band-clear)" tone="band">in-target +{pct("target_positive")}%</Chip>
        <Chip color="var(--band-high)" tone="band">in-target −{pct("target_negative")}%</Chip>
        <Chip>outside −{pct("outside_negative")}%</Chip>
      </div>
      <div className="tiny mut" style={{ marginTop: 8, textAlign: "center" }}>{v.note}</div>
    </Card>
  );
}

/* ── Band 4c: comparison with previous campaigns ── */
export function CampaignComparison({ report }: { report: Report }) {
  const c = report.campaign_comparison;
  if (!c.available) return <Card title="Similar past campaigns"><Empty>No similar campaigns in the corpus yet — run the news sync.</Empty></Card>;
  return (
    <Card title="Compared to similar past campaigns">
      <div className="stack">
        {c.matches.map((m, i) => (
          <div key={i} className="cmp" tabIndex={0}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong className="tiny">{m.brand || m.source}</strong>
              <Chip>{(m.similarity * 100).toFixed(0)}% similar</Chip>
            </div>
            <div className="tiny" style={{ margin: "4px 0" }}>{m.title}</div>
            {m.outcome && <div className="tiny mut">→ {m.outcome}</div>}
            {m.scores && (
              <div className="cmp-bars">
                {Object.entries(m.scores).map(([k, val]) => (
                  <div key={k} className="cmp-bar" title={`${k} ${(val * 100).toFixed(0)}`}>
                    <div style={{ height: `${val * 100}%`, background: val > 0.6 ? "var(--band-high)" : "var(--cat-3)" }} />
                  </div>
                ))}
              </div>
            )}
            {!m.is_reliable && m.caveat && <div className="tiny" style={{ color: "var(--band-elevated)", marginTop: 4 }}>⚠ {m.caveat}</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── Band 4d: risk anatomy radar ── */
const RISK_SHORT: Record<string, string> = {
  misinterpretation: "Misread", cultural: "Cultural", religious: "Religious",
  tone_mismatch: "Tone", confusion: "Confusion", meme_potential: "Meme", polarization: "Polarize",
};
export function RiskAnatomyRadar({ report }: { report: Report }) {
  const dims = Object.entries(report.risk.risk_anatomy);
  const n = dims.length, cx = 100, cy = 100, R = 78;
  const pt = (i: number, val: number) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * R * val, cy + Math.sin(a) * R * val];
  };
  const poly = dims.map(([, v], i) => pt(i, v).join(",")).join(" ");
  return (
    <Card title="Risk Anatomy">
      <svg viewBox="0 0 200 200" className="radar">
        {[0.25, 0.5, 0.75, 1].map((r) => <circle key={r} cx={cx} cy={cy} r={R * r} fill="none" stroke="var(--hairline)" strokeWidth="0.8" />)}
        {dims.map(([], i) => { const [x, y] = pt(i, 1); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--hairline)" strokeWidth="0.6" />; })}
        <polygon points={poly} fill="var(--lime)" fillOpacity="0.4" stroke="var(--ink)" strokeWidth="1.5" />
        {dims.map(([k], i) => { const [x, y] = pt(i, 1.2); return <text key={k} x={x} y={y} fontSize="8" fill="var(--text-secondary)" textAnchor="middle" dominantBaseline="middle">{RISK_SHORT[k] || k}</text>; })}
      </svg>
    </Card>
  );
}
