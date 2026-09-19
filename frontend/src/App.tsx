import { useEffect, useMemo, useState } from "react";
import { api, type Report, type RewriteResult } from "./lib/api";
import { DEMO_REPORT, DEMO_REWRITE } from "./lib/demo";
import { Card, IconButton, ScoreGauge, Chip, Empty, Meter } from "./components/ui";
import {
  IntentVsInterpretation,
  WhatTheyThink,
  EmotionalResponse,
  PersonaReactions,
  SimulatedComments,
  RiskAnatomy,
  SeverityLikelihood,
  ControversialVsMisunderstood,
  WhoMightMisunderstand,
  RegionHeatmap,
  TargetVsUnintended,
  MemePotential,
} from "./panels/panels";
import { TriggerView, BacklashPathway, BlindSpots, Rewrites } from "./panels/special";

const DEMO = {
  copy: "Our new protein bar — finally, a beef bar that doesn't taste like a cow.",
  intent: "Position our protein bar as great-tasting and high in protein.",
};

const QUESTIONS = [
  { key: "understand", emoji: "🧠", title: "What did they understand?" },
  { key: "feel", emoji: "❤️", title: "How did they feel?" },
  { key: "risk", emoji: "⚠️", title: "Why might they react badly?" },
  { key: "who", emoji: "🎯", title: "Who is affected?" },
  { key: "cause", emoji: "🔍", title: "What exactly caused it?" },
] as const;

type View = "compose" | "analysis" | "rewrites";

export default function App() {
  const [copy, setCopy] = useState(DEMO.copy);
  const [intent, setIntent] = useState(DEMO.intent);
  const [scenario, setScenario] = useState("dietary_controversy_india");
  const [scenarios, setScenarios] = useState<string[]>(["quiet"]);
  const [report, setReport] = useState<Report | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [rwLoading, setRwLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("compose");
  const [health, setHealth] = useState<string>("");
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    api.scenarios().then((s) => setScenarios(s.scenarios)).catch(() => {});
    api.health().then((h) => setHealth(`${h.personas_loaded} personas · ${h.anthropic_auth}`)).catch((e) => setHealth(`backend unreachable: ${e.message}`));
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const runId = useMemo(() => report?.run_id, [report]);

  function loadDemo() {
    // Hardcoded showcase — no backend needed. Loads a full report + rewrites
    // from the "beef bar" case so every card is populated with realistic data.
    setError(null);
    setCopy(DEMO_REPORT.copy);
    setIntent(DEMO_REPORT.brand_intent || "");
    setReport(DEMO_REPORT);
    setRewrite(DEMO_REWRITE);
    setView("analysis");
  }

  async function run() {
    setLoading(true);
    setError(null);
    setRewrite(null);
    try {
      const res = await api.simulate({ copy, brand_intent: intent, context_scenario: scenario });
      setReport(res.report);
      setView("analysis");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function doRewrite() {
    if (!runId) return;
    setRwLoading(true);
    setView("rewrites");
    try {
      setRewrite(await api.rewrite(runId));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRwLoading(false);
    }
  }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar__logo">c</div>
        <IconButton title="Compose" active={view === "compose"} onClick={() => setView("compose")}>✎</IconButton>
        <IconButton title="Analysis" active={view === "analysis"} onClick={() => report && setView("analysis")}>▤</IconButton>
        <IconButton title="Rewrites" active={view === "rewrites"} onClick={() => report && setView("rewrites")}>↻</IconButton>
        <div className="sidebar__spacer" />
        <IconButton title="Toggle theme" onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}>
          {theme === "light" ? "☾" : "☀"}
        </IconButton>
      </nav>

      <main className="main">
        <header className="topbar">
          <div>
            <h1 className="topbar__title">crowdLens</h1>
            <div className="topbar__sub">{health || "connecting…"}</div>
          </div>
          <div className="topbar__spacer" />
          <button className="btn btn--accent" onClick={loadDemo} title="Load a full hardcoded demo — no backend needed">
            ▶ Demo
          </button>
          {report && (
            <div className="tabs">
              {(["compose", "analysis", "rewrites"] as View[]).map((v) => (
                <button key={v} className={`tab ${view === v ? "tab--active" : ""}`} onClick={() => setView(v)}>
                  {v === "compose" ? "Compose" : v === "analysis" ? "Analysis" : "Rewrites"}
                </button>
              ))}
            </div>
          )}
        </header>

        {error && <div className="alert" style={{ borderLeftColor: "var(--band-severe)" }}><strong>Error:</strong> {error}</div>}

        {view === "compose" && (
          <Composer
            copy={copy}
            setCopy={setCopy}
            intent={intent}
            setIntent={setIntent}
            scenario={scenario}
            setScenario={setScenario}
            scenarios={scenarios}
            onRun={run}
            loading={loading}
            report={report}
          />
        )}

        {view === "analysis" && report && <Analysis report={report} onRewrite={doRewrite} />}
        {view === "analysis" && !report && <Empty>Run a simulation from Compose first.</Empty>}

        {view === "rewrites" && (
          <div className="qsection">
            <div className="qsection__head">
              <span className="qsection__emoji">✏️</span>
              <h3 className="qsection__title">Rewrite Suggestions</h3>
              {report && !rewrite && !rwLoading && (
                <button className="btn btn--accent" onClick={doRewrite} style={{ marginLeft: "auto" }}>Generate rewrites</button>
              )}
            </div>
            <Rewrites result={rewrite} loading={rwLoading} />
          </div>
        )}
      </main>
    </div>
  );
}

function Composer(props: {
  copy: string;
  setCopy: (s: string) => void;
  intent: string;
  setIntent: (s: string) => void;
  scenario: string;
  setScenario: (s: string) => void;
  scenarios: string[];
  onRun: () => void;
  loading: boolean;
  report: Report | null;
}) {
  const { copy, setCopy, intent, setIntent, scenario, setScenario, scenarios, onRun, loading, report } = props;
  return (
    <div className="composer">
      <div>
        <div className="field">
          <label className="field__label">Marketing copy</label>
          <textarea className="editor" value={copy} onChange={(e) => setCopy(e.target.value)} placeholder="Paste the copy you want to test…" />
        </div>
        <div className="field">
          <label className="field__label">What you meant to say (brand intent)</label>
          <input className="input" value={intent} onChange={(e) => setIntent(e.target.value)} placeholder="The message you intend to land…" />
        </div>
        <div className="row">
          <div style={{ flex: 1 }}>
            <label className="field__label">Context scenario</label>
            <select className="select" value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {scenarios.map((s) => (
                <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <button className="btn btn--primary" style={{ alignSelf: "flex-end", height: 44 }} onClick={onRun} disabled={loading || !copy.trim()}>
            {loading ? "Simulating…" : "Run simulation"}
          </button>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <span className={`provenance provenance--mock`}>mock context</span>
          <span className="tiny mut">Live GDELT/RSS context is wired in the backend; fixtures shown here.</span>
        </div>
      </div>

      <Card raised title="Result">
        {loading ? (
          <div className="spinner" style={{ margin: "48px auto" }} />
        ) : report ? (
          <>
            <ScoreGauge value={report.risk_index.value} band={report.risk_index.band} interval={report.risk_index.interval} />
            {report.risk_index.override_fired && (
              <div className="tiny" style={{ marginTop: 8, color: "var(--band-high)" }}>
                ⚑ Band raised: a credible severe reaction can't be averaged away.
              </div>
            )}
            <div style={{ marginTop: 20 }}>
              <Meter value={report.intent_alignment.value} max={100} color="var(--cat-3)" label={<span>Intent Alignment<span className="tabular">{report.intent_alignment.value.toFixed(0)}%</span></span>} />
            </div>
            <p className="disclaimer">{report.risk_index.disclaimer}</p>
          </>
        ) : (
          <Empty>Run a simulation to see the Risk Index, its confidence interval, and the full analysis.</Empty>
        )}
      </Card>
    </div>
  );
}

function Analysis({ report, onRewrite }: { report: Report; onRewrite: () => void }) {
  return (
    <div>
      {/* Headline row */}
      <div className="grid" style={{ marginBottom: 32 }}>
        <Card raised span={4} title={report.risk_index.label}>
          <ScoreGauge value={report.risk_index.value} band={report.risk_index.band} interval={report.risk_index.interval} />
        </Card>
        <Card span={4} title="Intent Alignment Score">
          <div className="big-num tabular">{report.intent_alignment.value.toFixed(0)}<sup>%</sup></div>
          <div className="tiny mut" style={{ marginTop: 8 }}>Share of the audience that understood the intended message. A campaign can be safe and still fail here.</div>
        </Card>
        <Card span={4} inverted title="Context">
          <div className="big-num tabular" style={{ color: "#fff" }}>{report.risk_index.components.context_multiplier.toFixed(2)}×</div>
          <div className="tiny" style={{ color: "rgba(255,255,255,.6)", marginTop: 8 }}>{report.context.scenario.replace(/_/g, " ")}</div>
          <div style={{ marginTop: 12 }}>
            <span className={`provenance provenance--${report.context.provenance === "mock" ? "mock" : "live"}`}>{report.context.provenance}</span>
          </div>
        </Card>
      </div>

      {report.control_canary?.fired && (
        <div className="alert"><strong>⚙ Calibration warning:</strong> {report.control_canary.message}</div>
      )}

      {/* 🧠 */}
      <QSection q={QUESTIONS[0]}>
        <div className="grid">
          <IntentVsInterpretation report={report} />
          <WhatTheyThink report={report} />
        </div>
      </QSection>

      {/* ❤️ */}
      <QSection q={QUESTIONS[1]}>
        <div className="grid">
          <EmotionalResponse report={report} />
          <SimulatedComments report={report} />
          <PersonaReactions report={report} />
        </div>
      </QSection>

      {/* ⚠️ */}
      <QSection q={QUESTIONS[2]}>
        <div className="grid">
          <RiskAnatomy report={report} />
          <SeverityLikelihood report={report} />
          <ControversialVsMisunderstood report={report} />
        </div>
      </QSection>

      {/* 🎯 */}
      <QSection q={QUESTIONS[3]}>
        <div className="grid">
          <WhoMightMisunderstand report={report} />
          <RegionHeatmap report={report} />
          <TargetVsUnintended report={report} />
        </div>
      </QSection>

      {/* 🔍 */}
      <QSection q={QUESTIONS[4]}>
        <div className="grid">
          <TriggerView report={report} />
          <BacklashPathway report={report} />
          <MemePotential report={report} />
        </div>
      </QSection>

      <BlindSpots report={report} />

      <div className="row" style={{ justifyContent: "center", margin: "24px 0" }}>
        <button className="btn btn--accent" onClick={onRewrite}>✏️ Fix it — generate rewrites</button>
      </div>
    </div>
  );
}

function QSection({ q, children }: { q: (typeof QUESTIONS)[number]; children: React.ReactNode }) {
  return (
    <section className="qsection">
      <div className="qsection__head">
        <span className="qsection__emoji">{q.emoji}</span>
        <h3 className="qsection__title">{q.title}</h3>
      </div>
      {children}
    </section>
  );
}
