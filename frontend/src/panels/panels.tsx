/* Dashboard panels — projections of the report, one per analysis. */

import type { Report } from "../lib/api";
import { BAND_COLOR } from "../lib/api";
import { Card, Chip, Meter, Empty, emotionColor } from "../components/ui";

const RISK_LABELS: Record<string, string> = {
  misinterpretation: "Misinterpretation",
  cultural: "Cultural",
  religious: "Religious",
  tone_mismatch: "Tone mismatch",
  confusion: "Confusion",
  meme_potential: "Meme potential",
  polarization: "Polarization",
};

function initials(label: string) {
  return label.split(/[\s,]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

/* ── 🧠 Intent vs Interpretation ── */
export function IntentVsInterpretation({ report }: { report: Report }) {
  const rows = report.understanding.intent_vs_interpretation;
  return (
    <Card title="Intent vs. Interpretation" span={7}>
      <div className="stack">
        {rows.slice(0, 6).map((r) => (
          <div key={r.persona_id} className="persona" style={{ padding: 12 }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="persona__label">{r.label}</span>
              <Chip>{r.comprehension}</Chip>
            </div>
            <div className="tiny mut" style={{ marginTop: 4 }}>They read it as: "{r.perceived_intent}"</div>
            <Meter value={r.gap} color={r.gap > 0.5 ? "var(--band-high)" : "var(--cat-3)"} label={<span>interpretation gap<span className="tabular">{(r.gap * 100).toFixed(0)}%</span></span>} />
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── 🧠 What They Think You're Saying ── */
export function WhatTheyThink({ report }: { report: Report }) {
  const clusters = report.understanding.what_they_think_youre_saying;
  return (
    <Card title="What They Think You're Saying" span={5}>
      {clusters.length === 0 ? (
        <Empty>No interpretations captured.</Empty>
      ) : (
        <div className="stack">
          {clusters.map((c, i) => (
            <div key={i} className="persona" style={{ padding: 14, background: i === 0 ? "var(--surface)" : undefined }}>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span className="tabular" style={{ fontSize: 20, fontWeight: 300 }}>{(c.share * 100).toFixed(0)}%</span>
                <Chip>{c.size} {c.size === 1 ? "persona" : "personas"}</Chip>
              </div>
              <div style={{ fontSize: 15 }}>"{c.label}"</div>
            </div>
          ))}
          <div className="tiny mut">The largest reading that is not your intended one is what most of your audience thinks you said.</div>
        </div>
      )}
    </Card>
  );
}

/* ── ❤️ Emotional Response ── */
export function EmotionalResponse({ report }: { report: Report }) {
  const er = report.feeling.emotional_response;
  const entries = Object.entries(er.distribution).sort((a, b) => b[1] - a[1]);
  return (
    <Card title="Emotional Response" span={5}>
      <div className="stack">
        <div style={{ display: "flex", height: 40, borderRadius: 8, overflow: "hidden", boxShadow: "var(--shadow-card)" }}>
          {entries.map(([e, v]) => (
            <div key={e} title={`${e} ${(v * 100).toFixed(0)}%`} style={{ width: `${v * 100}%`, background: emotionColor(e) }} />
          ))}
        </div>
        <div className="row" style={{ gap: 6, marginTop: 8 }}>
          {entries.map(([e, v]) => (
            <Chip key={e}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: emotionColor(e), display: "inline-block" }} />
              {e} {(v * 100).toFixed(0)}%
            </Chip>
          ))}
        </div>
        {er.polarization > 0.3 && (
          <div className="gauge__split" style={{ marginTop: 12 }}>
            ⚡ Polarization {(er.polarization * 100).toFixed(0)}% — the audience splits into strong love and strong hate.
          </div>
        )}
      </div>
    </Card>
  );
}

/* ── ❤️ Persona Reactions ── */
export function PersonaReactions({ report }: { report: Report }) {
  const rs = report.feeling.persona_reactions;
  return (
    <Card title="Persona Reactions" span={12}>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
        {rs.map((p) => (
          <div key={p.persona_id} className="persona">
            <div className="persona__head">
              <span className="persona__label">{p.label}</span>
              <Chip>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: emotionColor(p.emotion), display: "inline-block" }} />
                {p.emotion}
              </Chip>
            </div>
            <Meter value={p.severity} color={p.severity > 0.6 ? "var(--band-high)" : "var(--cat-3)"} label={<span>severity<span className="tabular">{(p.severity * 100).toFixed(0)}</span></span>} />
            <div className="persona__readings">
              <div className="reading">
                <div className="reading__k">Charitable</div>
                {p.charitable_reading}
              </div>
              <div className="reading">
                <div className="reading__k">Hostile</div>
                {p.hostile_reading}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── ❤️ Simulated Comments ── */
export function SimulatedComments({ report }: { report: Report }) {
  const cs = report.feeling.simulated_comments;
  return (
    <Card title="Simulated Comment Section" span={7}>
      <div>
        {cs.slice(0, 10).map((c, i) => (
          <div key={i} className="comment">
            <div className="avatar">{initials(c.label)}</div>
            <div className="comment__body">
              <div className="comment__meta">
                {c.label} · <span style={{ color: emotionColor(c.emotion) }}>{c.tone}</span>
              </div>
              <div className="comment__text">{c.text}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── ⚠️ Risk Anatomy (radar) ── */
export function RiskAnatomy({ report }: { report: Report }) {
  const dims = Object.entries(report.risk.risk_anatomy);
  const n = dims.length;
  const cx = 130, cy = 130, R = 100;
  const pt = (i: number, val: number) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    return [cx + Math.cos(a) * R * val, cy + Math.sin(a) * R * val];
  };
  const poly = dims.map(([, v], i) => pt(i, v).join(",")).join(" ");
  return (
    <Card title="Risk Anatomy" span={5}>
      <svg className="radar" width="260" height="260" viewBox="0 0 260 260">
        {[0.25, 0.5, 0.75, 1].map((r) => (
          <circle key={r} cx={cx} cy={cy} r={R * r} fill="none" stroke="var(--hairline)" strokeWidth="1" />
        ))}
        {dims.map(([, ], i) => {
          const [x, y] = pt(i, 1);
          return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--hairline)" strokeWidth="1" />;
        })}
        <polygon points={poly} fill="var(--lime)" fillOpacity="0.35" stroke="var(--ink)" strokeWidth="1.5" />
        {dims.map(([k], i) => {
          const [x, y] = pt(i, 1.22);
          return (
            <text key={k} x={x} y={y} fontSize="9" fill="var(--text-secondary)" textAnchor="middle" dominantBaseline="middle">
              {RISK_LABELS[k]?.split(" ")[0] || k}
            </text>
          );
        })}
      </svg>
    </Card>
  );
}

/* ── ⚠️ Severity × Likelihood ── */
export function SeverityLikelihood({ report }: { report: Report }) {
  const rows = report.risk.severity_likelihood.filter((r) => r.likelihood > 0 || r.severity > 0);
  return (
    <Card title="Severity × Likelihood" span={4}>
      <div className="matrix">
        <div className="matrix__q" style={{ top: 0, right: 0 }}>Fix Now</div>
        <div className="matrix__q" style={{ bottom: 0, right: 0 }}>Contain</div>
        <div className="matrix__q" style={{ top: 0, left: 0 }}>Prepare</div>
        <div className="matrix__q" style={{ bottom: 0, left: 0 }}>Monitor</div>
        {rows.map((r) => (
          <div
            key={r.dimension}
            className="matrix__pt"
            title={`${RISK_LABELS[r.dimension]}: sev ${(r.severity * 100).toFixed(0)}, likelihood ${(r.likelihood * 100).toFixed(0)}`}
            style={{
              left: `${r.likelihood * 100}%`,
              bottom: `${r.severity * 100}%`,
              background: r.quadrant === "Fix Now" ? "var(--band-severe)" : "var(--ink)",
              width: 10 + r.affected_personas.length * 3,
              height: 10 + r.affected_personas.length * 3,
            }}
          />
        ))}
      </div>
      <div className="tiny mut" style={{ marginTop: 8 }}>x: likelihood (audience share) · y: severity</div>
    </Card>
  );
}

/* ── ⚠️ Controversial vs Misunderstood ── */
export function ControversialVsMisunderstood({ report }: { report: Report }) {
  const cvm = report.risk.controversial_vs_misunderstood;
  return (
    <Card title="Controversial vs. Misunderstood" span={8}>
      <div className="row" style={{ gap: 8 }}>
        {Object.entries(cvm.mass)
          .sort((a, b) => b[1] - a[1])
          .map(([q, m]) => (
            <div key={q} className="persona" style={{ flex: 1, minWidth: 140, padding: 14 }}>
              <div className="tabular" style={{ fontSize: 24, fontWeight: 300 }}>{(m * 100).toFixed(0)}%</div>
              <div style={{ fontWeight: 500, fontSize: 14, margin: "4px 0" }}>{q}</div>
              <div className="tiny mut">{cvm.prescriptions[q]}</div>
            </div>
          ))}
      </div>
    </Card>
  );
}

/* ── 🎯 Who Might Misunderstand ── */
export function WhoMightMisunderstand({ report }: { report: Report }) {
  const rows = report.who.who_might_misunderstand;
  return (
    <Card title="Who Might Misunderstand?" span={6}>
      {rows.length === 0 ? (
        <Empty>Everyone understood the intended message.</Empty>
      ) : (
        <div className="stack">
          {rows.map((r) => (
            <div key={r.persona_id} className="persona" style={{ padding: 12 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="persona__label">{r.label}</span>
                <Chip color="var(--band-high)" tone="band">{r.comprehension}</Chip>
              </div>
              <div className="tiny mut" style={{ marginTop: 4 }}>reads it as: "{r.they_think_you_said}"</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/* ── 🎯 Region Heatmap ── */
export function RegionHeatmap({ report }: { report: Report }) {
  const rows = report.who.region_heatmap;
  return (
    <Card title="Region Heatmap" span={6}>
      <div className="stack">
        {rows.map((r) => (
          <div key={r.region} className="row" style={{ justifyContent: "space-between", gap: 12 }}>
            <span style={{ width: 60, fontWeight: 500 }}>{r.region}</span>
            <div style={{ flex: 1, height: 24, borderRadius: 8, background: "var(--surface-raised)", position: "relative", overflow: "hidden" }}>
              <div style={{ width: `${r.mean_severity * 100}%`, height: "100%", background: r.mean_severity > 0.6 ? "var(--band-high)" : "var(--lime)", borderRadius: 8 }} />
            </div>
            <span className="tabular tiny mut" style={{ width: 36 }}>{(r.mean_severity * 100).toFixed(0)}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── 🎯 Target vs Unintended ── */
export function TargetVsUnintended({ report }: { report: Report }) {
  const tvu = report.who.target_vs_unintended;
  const cell = (d: Record<string, unknown>, title: string) => (
    <div className="persona" style={{ flex: 1, padding: 14 }}>
      <div className="reading__k">{title}</div>
      <div className="big-num tabular">{d.mean_severity != null ? ((d.mean_severity as number) * 100).toFixed(0) : "—"}</div>
      <div className="tiny mut">{(d.persona_count as number) || 0} personas · IAS {d.mean_intent_alignment != null ? ((d.mean_intent_alignment as number) * 100).toFixed(0) + "%" : "—"}</div>
    </div>
  );
  return (
    <Card title="Target vs. Unintended Audience" span={6}>
      <div className="row" style={{ gap: 12 }}>
        {cell(tvu.target, "Target")}
        {cell(tvu.unintended, "Unintended")}
      </div>
      {tvu.severity_gap != null && (
        <div className="tiny mut" style={{ marginTop: 12 }}>
          Severity gap: {(tvu.severity_gap * 100).toFixed(0)} — the wider this is, the more the people who screenshot you differ from your target.
        </div>
      )}
    </Card>
  );
}

/* ── 🔍 Meme Potential ── */
export function MemePotential({ report }: { report: Report }) {
  const mp = report.cause.meme_potential;
  return (
    <Card title="Meme / Virality Potential" span={5}>
      <div className="big-num tabular">{(mp.score * 100).toFixed(0)}<sup>/100</sup></div>
      <div className="tiny mut">{mp.would_share_mocking.length} personas would share this mockingly · {(mp.mocking_audience_mass * 100).toFixed(0)}% of audience</div>
      {mp.candidate_spans.length > 0 && (
        <div className="stack" style={{ marginTop: 12 }}>
          {mp.candidate_spans.slice(0, 4).map((s, i) => (
            <div key={i} className="row" style={{ justifyContent: "space-between" }}>
              <Chip tone="accent">"{s.span}"</Chip>
              <span className="tabular tiny mut">{(s.meme_potential * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
