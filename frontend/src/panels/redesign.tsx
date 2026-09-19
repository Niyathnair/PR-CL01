/* Panels for the four-band redesign: L1 strip, feel+word-cloud, campaign
   highlight+rewrites, persona illustrations, India map, target Venn, comparison,
   risk anatomy. */

import type { Report } from "../lib/api";
import { BAND_COLOR, type Band } from "../lib/api";
import { Card, Chip, BandChip, Empty, emotionColor } from "../components/ui";

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

/* ── Band 2 left-upper: How do they feel (bar chart) ── */
export function FeelChart({ report }: { report: Report }) {
  const er = report.feeling.emotional_response;
  const entries = Object.entries(er.distribution).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map((e) => e[1]), 0.01);
  return (
    <Card title="How do they feel?">
      <div className="feelbars">
        {entries.map(([e, v]) => (
          <div key={e} className="feelbar">
            <div className="feelbar__col" style={{ height: `${(v / max) * 100}%`, background: emotionColor(e) }} />
            <div className="feelbar__pct tabular">{(v * 100).toFixed(0)}</div>
            <div className="feelbar__lbl">{e}</div>
          </div>
        ))}
      </div>
      {er.polarization > 0.3 && (
        <div className="split-note">⚡ Polarization {(er.polarization * 100).toFixed(0)}% — strong love and strong hate.</div>
      )}
    </Card>
  );
}

/* ── Band 2 left-lower: comment word-cloud (size ∝ how many react that way) ── */
export function CommentCloud({ report }: { report: Report }) {
  const cs = report.feeling.simulated_comments;
  // Size by prevalence weight; color by emotion.
  const maxW = Math.max(...cs.map((c) => c.weight), 0.01);
  return (
    <Card title="What they're saying">
      <div className="cloud">
        {cs.map((c, i) => {
          const scale = 0.8 + (c.weight / maxW) * 1.1;
          return (
            <span
              key={i}
              className="cloud__word"
              style={{ fontSize: `${scale}em`, color: emotionColor(c.emotion) }}
              title={`${c.label} · ${c.tone}`}
            >
              "{c.text}"
            </span>
          );
        })}
      </div>
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

/* ── Band 3: persona illustrations, positive left / negative right ── */
function PersonaFace({ p }: { p: Report["feeling"]["persona_reactions"][0] }) {
  const positive = p.sentiment === "favorable";
  const negative = p.sentiment === "opposed";
  const feeling = negative ? "offended" : positive ? "likes it" : "neutral";
  const pct = Math.round(p.severity * 100);
  const short = p.label.length > 28 ? p.label.slice(0, 28) + "…" : p.label;
  // Simple demographic-driven avatar: color by region-ish hash, emoji by emotion.
  const emoji = { offended: "😠", uncomfortable: "😟", confused: "😕", neutral: "😐", curious: "🤔", amused: "😄", positive: "😊" }[p.emotion] || "🙂";
  return (
    <div className="face" tabIndex={0}>
      <div className="face__top">
        <span className="face__feel" style={{ color: negative ? "var(--band-high)" : positive ? "var(--band-clear)" : "var(--text-secondary)" }}>
          {feeling} {negative || positive ? `${pct}%` : ""}
        </span>
      </div>
      <div className="face__emoji" style={{ background: emotionColor(p.emotion) }}>{emoji}</div>
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

/* ── Band 4a: India region heatmap (schematic map) ── */
const IN_POS: Record<string, [number, number]> = {
  DL: [46, 30], PB: [40, 24], HR: [44, 30], RJ: [34, 38], GJ: [26, 50],
  MH: [38, 58], MP: [46, 46], UP: [54, 36], BR: [64, 40], WB: [70, 48],
  AS: [82, 40], KA: [42, 72], TG: [50, 62], AP: [52, 70], TN: [46, 84], KL: [40, 84],
};
export function IndiaHeatmap({ report }: { report: Report }) {
  const geo = report.geo_india;
  const color = (t: number) => (t > 0.15 ? "var(--band-high)" : t < -0.15 ? "var(--band-clear)" : "var(--cat-7)");
  return (
    <Card title="India — regional response">
      {!geo.available ? (
        <Empty>No India regional signal.</Empty>
      ) : (
        <>
          <svg viewBox="0 0 100 100" className="india-map">
            <path d="M40 18 L58 20 L64 32 L82 36 L80 46 L66 50 L62 60 L54 68 L48 88 L42 86 L38 66 L26 56 L24 46 L30 38 L34 26 Z" fill="var(--surface-raised)" stroke="var(--hairline)" strokeWidth="0.6" />
            {geo.states.map((s) => {
              const pos = IN_POS[s.code];
              if (!pos) return null;
              return (
                <circle key={s.code} cx={pos[0]} cy={pos[1]} r={2.4 + Math.abs(s.intensity) * 2.4}
                  fill={color(s.intensity)} fillOpacity={0.55 + Math.abs(s.intensity) * 0.4}>
                  <title>{s.name}: {s.intensity > 0 ? "offended" : "favourable"} {Math.abs(s.intensity * 100).toFixed(0)}%</title>
                </circle>
              );
            })}
          </svg>
          <div className="row" style={{ gap: 12, marginTop: 8 }}>
            <Chip><span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--band-high)", display: "inline-block" }} /> offended</Chip>
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
