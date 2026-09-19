/* Panels that render structure rather than plain metrics: trigger-highlighted
   copy, the backlash pathway graph, Tier-2 blind spots, rewrites. */

import { useState } from "react";
import type { Report, RewriteResult } from "../lib/api";
import { BAND_COLOR } from "../lib/api";
import { Card, Chip, BandChip, Empty, Meter } from "../components/ui";

/* ── 🔍 Trigger-highlighted copy — the composer's primary surface ── */
export function TriggerView({ report }: { report: Report }) {
  const copy = report.copy;
  const spans = [...report.cause.trigger_index].sort((a, b) => a.char_start - b.char_start);

  // Build non-overlapping segments.
  const segs: { text: string; trig?: (typeof spans)[0] }[] = [];
  let cursor = 0;
  for (const s of spans) {
    if (s.char_start < cursor) continue; // skip overlaps
    if (s.char_start > cursor) segs.push({ text: copy.slice(cursor, s.char_start) });
    segs.push({ text: copy.slice(s.char_start, s.char_end), trig: s });
    cursor = s.char_end;
  }
  if (cursor < copy.length) segs.push({ text: copy.slice(cursor) });

  const level = (sev: number) => (sev > 0.75 ? 3 : sev > 0.4 ? 2 : 1);

  return (
    <Card title="Trigger Detection" span={7}>
      <div className="copy-view">
        {segs.map((s, i) =>
          s.trig ? (
            <span key={i} className={`trig trig--${level(s.trig.max_severity)}`} title={`${s.trig.persona_count} persona(s): ${s.trig.personas[0]?.why || ""}`}>
              {s.text}
            </span>
          ) : (
            <span key={i}>{s.text}</span>
          )
        )}
      </div>
      {spans.length === 0 ? (
        <Empty>No triggers flagged.</Empty>
      ) : (
        <div className="stack" style={{ marginTop: 16 }}>
          {spans.slice(0, 5).map((s, i) => (
            <div key={i} className="row" style={{ justifyContent: "space-between" }}>
              <Chip tone="accent">"{s.span}"</Chip>
              <span className="tiny mut">{s.persona_count} affected · {s.modality}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

/* ── 🔍 Backlash Pathway ── */
export function BacklashPathway({ report }: { report: Report }) {
  const bp = report.cause.backlash_pathway;
  return (
    <Card title="Backlash Pathway" span={5}>
      <div className="pathway">
        {bp.nodes.map((n, i) => (
          <div key={n.id}>
            <div className="pathnode">
              <div className="pathnode__stage">{n.stage.replace("_", " ")}</div>
              <div className="pathnode__label">{n.label}</div>
              <div className="pathnode__detail">"{n.detail}"</div>
            </div>
            {i < bp.edges.length && (
              <div className="pathedge">
                <div className="pathedge__arrow">↓</div>
                <span className="tabular">{(bp.edges[i].likelihood * 100).toFixed(0)}% likely</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {bp.terminated_at && bp.termination_reason && (
        <div className="pathterm">✋ {bp.termination_reason}</div>
      )}
      <div className="tiny mut" style={{ marginTop: 12 }}>
        Overall likelihood {(bp.overall_likelihood * 100).toFixed(0)}%. Every node is a real persona's own words, never invented.
      </div>
    </Card>
  );
}

/* ── Blind Spot Findings (Tier 2) — visually quarantined ── */
export function BlindSpots({ report }: { report: Report }) {
  const findings = report.blind_spot_findings;
  if (findings.length === 0) return null;
  return (
    <div className="qsection">
      <div className="qsection__head">
        <span className="qsection__emoji">🕳️</span>
        <h3 className="qsection__title">Blind Spot Findings</h3>
        <Chip>not scored</Chip>
      </div>
      {report.severe_discovery_alert && (
        <div className="alert">
          <div className="alert__title">⚠ Severe Discovery Alert</div>
          <p style={{ margin: "8px 0" }}>{report.severe_discovery_alert.message}</p>
          <div className="tiny mut">"{report.severe_discovery_alert.comment}"</div>
        </div>
      )}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {findings.map((f) => (
          <div key={f.composite_id} className="blindspot">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="blindspot__tag">Simulated intersection</span>
              <span className="blindspot__tag">not scored</span>
            </div>
            <div style={{ fontSize: 15, margin: "8px 0" }}>"{f.paraphrase}"</div>
            <div className="tiny mut">"{f.comment}"</div>
            <div className="blindspot__caveat">{f.disclaimer}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── ✏️ Rewrites + 🔄 Before/After ── */
export function Rewrites({ result, loading }: { result: RewriteResult | null; loading: boolean }) {
  if (loading) return <div className="spinner" style={{ margin: "48px auto" }} />;
  if (!result) return <Empty>Run a simulation, then generate rewrites to see them re-scored here.</Empty>;

  return (
    <div className="stack" style={{ gap: 16 }}>
      <Card title="Original" span={12}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div style={{ fontSize: 17, flex: 1 }}>"{result.original.text}"</div>
          <div className="row">
            <span className="big-num tabular">{result.original.risk_index.toFixed(0)}</span>
            <BandChip band={result.original.band} />
          </div>
        </div>
      </Card>
      {!result.any_improved && result.note && (
        <div className="pathterm">{result.note}</div>
      )}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
        {result.variants.map((v) => (
          <Card key={v.kind} raised>
            <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <Chip tone={v.kind === result.best_variant ? "accent" : "neutral"}>{v.kind.replace("_", " ")}</Chip>
              {v.improved && <Chip>improved ↓</Chip>}
            </div>
            <div style={{ fontSize: 16, marginBottom: 12 }}>"{v.text}"</div>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <span className="big-num tabular">{v.risk_index.toFixed(0)}</span> <BandChip band={v.band} />
              </div>
              <div className="tiny mut">IAS {v.intent_alignment.toFixed(0)}%</div>
            </div>
            <Meter value={v.risk_index} max={100} color={BAND_COLOR[v.band]} />
            {v.resolved_triggers.length > 0 && (
              <div className="tiny" style={{ marginTop: 8 }}>
                ✓ resolved: {v.resolved_triggers.map((t) => `"${t}"`).join(", ")}
              </div>
            )}
            {v.new_triggers.length > 0 && (
              <div className="tiny" style={{ marginTop: 4, color: "var(--band-high)" }}>
                ⚠ new: {v.new_triggers.map((t) => `"${t}"`).join(", ")}
              </div>
            )}
            <div className="tiny mut" style={{ marginTop: 8 }}>
              <strong>Sacrificed:</strong> {v.sacrificed || "nothing material"}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
