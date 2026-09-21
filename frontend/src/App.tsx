import { useEffect, useState } from "react";
import { api, type Report, type RewriteResult } from "./lib/api";
import { DEMO_REPORT, DEMO_REWRITE } from "./lib/demo";
import { Card, IconButton, Empty } from "./components/ui";
import {
  L1Strip,
  FeelChart,
  CommentCloud,
  CampaignHighlight,
  PersonaBoards,
  IndiaHeatmap,
  TargetVenn,
  CampaignComparison,
  RiskAnatomyRadar,
} from "./panels/redesign";

const DEMO = {
  copy: "Our new protein bar — finally, a beef bar that doesn't taste like a cow.",
  intent: "Position our protein bar as great-tasting and high in protein.",
};

type View = "compose" | "dashboard";

export default function App() {
  const [copy, setCopy] = useState(DEMO.copy);
  const [intent, setIntent] = useState(DEMO.intent);
  const [scenario, setScenario] = useState("dietary_controversy_india");
  const [ageMin, setAgeMin] = useState(18);
  const [ageMax, setAgeMax] = useState(25);
  const [scenarios, setScenarios] = useState<string[]>(["quiet"]);
  const [report, setReport] = useState<Report | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [rwLoading, setRwLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("compose");
  const [health, setHealth] = useState<string>("");
  const [theme, setTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    api.scenarios().then((s) => setScenarios(s.scenarios)).catch(() => {});
    api.health().then((h) => setHealth(`${h.personas_loaded} personas`)).catch(() => setHealth("backend offline — use Demo"));
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  function loadDemo() {
    setError(null);
    setCopy(DEMO_REPORT.copy);
    setIntent(DEMO_REPORT.brand_intent || "");
    setReport(DEMO_REPORT);
    setRewrite(DEMO_REWRITE);
    setView("dashboard");
  }

  async function run() {
    setLoading(true);
    setError(null);
    setRewrite(null);
    try {
      const res = await api.simulate({
        copy,
        brand_intent: intent,
        context_scenario: scenario,
        target_age_min: ageMin,
        target_age_max: ageMax,
      });
      setReport(res.report);
      setView("dashboard");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function doRewrite() {
    if (!report) return;
    // Demo report already carries its rewrite.
    if (report === DEMO_REPORT) {
      setRewrite(DEMO_REWRITE);
      return;
    }
    setRwLoading(true);
    try {
      setRewrite(await api.rewrite(report.run_id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRwLoading(false);
    }
  }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar__brand">
          <div className="sidebar__logo">c</div>
          <div className="sidebar__wordmark">crowdLens</div>
        </div>

        <button
          className={`navitem ${view === "compose" ? "navitem--active" : ""}`}
          onClick={() => setView("compose")}
        >
          <span className="navitem__icon">✎</span> Compose
        </button>
        <button
          className={`navitem ${view === "dashboard" ? "navitem--active" : ""}`}
          onClick={() => report && setView("dashboard")}
          disabled={!report}
        >
          <span className="navitem__icon">▤</span> Dashboard
          {report && <span className="navitem__badge">live</span>}
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">◔</span> Personas
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">◈</span> Regions
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">✿</span> Rewrites
        </button>

        <div className="sidebar__section">Sources</div>
        <button className="navitem" disabled>
          <span className="navitem__icon">◒</span> Reddit
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">✕</span> X / Twitter
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">＋</span> Add source
        </button>

        <div className="sidebar__section">Workspace</div>
        <button className="navitem" disabled>
          <span className="navitem__icon">◇</span> History
        </button>
        <button className="navitem" disabled>
          <span className="navitem__icon">⚙</span> Settings
        </button>

        <div className="sidebar__spacer" />

        <IconButton title="Toggle theme" onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}>
          {theme === "light" ? "☾" : "☀"}
        </IconButton>

        <div className="sidebar__foot">
          <div className="sidebar__avatar">U</div>
          <div className="sidebar__who">
            <b>User</b>
            <span>Free plan</span>
          </div>
        </div>
      </nav>

      <main className="main main--full">
        <header className="topbar">
          <div>
            <h1 className="topbar__greet">Hi, <em>User!</em></h1>
            <div className="topbar__sub">{health || "connecting…"}</div>
          </div>
          <div className="topbar__spacer" />
          <button className="btn btn--accent" onClick={loadDemo}>▶ Demo</button>
          {report && (
            <div className="tabs">
              {(["compose", "dashboard"] as View[]).map((v) => (
                <button key={v} className={`tab ${view === v ? "tab--active" : ""}`} onClick={() => setView(v)}>
                  {v === "compose" ? "Compose" : "Dashboard"}
                </button>
              ))}
            </div>
          )}
          <div className="topcluster">
            <button className="topcluster__btn" title="Search" aria-label="Search">⌕</button>
            <button className="topcluster__btn" title="Notifications" aria-label="Notifications">◔</button>
            <div className="topcluster__avatar">U</div>
          </div>
        </header>

        {error && <div className="alert" style={{ borderLeftColor: "var(--band-severe)" }}><strong>Error:</strong> {error}</div>}

        {view === "compose" && (
          <Composer
            {...{ copy, setCopy, intent, setIntent, scenario, setScenario, scenarios, ageMin, setAgeMin, ageMax, setAgeMax, onRun: run, loading }}
          />
        )}

        {view === "dashboard" && report && (
          <Dashboard report={report} rewrite={rewrite} rwLoading={rwLoading} onRewrite={doRewrite} />
        )}
        {view === "dashboard" && !report && <Empty>Run a simulation or click Demo.</Empty>}
      </main>
    </div>
  );
}

function Composer(props: any) {
  const { copy, setCopy, intent, setIntent, scenario, setScenario, scenarios, ageMin, setAgeMin, ageMax, setAgeMax, onRun, loading } = props;
  return (
    <div className="compose-wrap">
      <div className="compose-hero">
        <span className="compose-hero__eyebrow">◇ Pre-launch backlash simulator</span>
        <h1 className="compose-hero__title">See who gets <em>hurt</em><br />before you hit publish.</h1>
        <p className="compose-hero__sub">
          Drop in your campaign copy. We simulate the audience — persona by persona, region by
          region — and show you the backlash before the internet does.
        </p>
      </div>
      <Card raised>
        <div className="field">
          <label className="field__label">Marketing copy</label>
          <textarea className="editor" value={copy} onChange={(e) => setCopy(e.target.value)} placeholder="Paste the copy you want to test…" />
        </div>
        <div className="field">
          <label className="field__label">What you meant to say (brand intent)</label>
          <input className="input" value={intent} onChange={(e) => setIntent(e.target.value)} />
        </div>
        <div className="row" style={{ gap: 16, alignItems: "flex-end" }}>
          <div style={{ flex: 2 }}>
            <label className="field__label">Context scenario</label>
            <select className="select" value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {scenarios.map((s: string) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label className="field__label">Target audience age</label>
            <div className="row" style={{ gap: 8 }}>
              <input className="input" type="number" value={ageMin} min={0} max={120} onChange={(e) => setAgeMin(+e.target.value)} />
              <span className="mut">–</span>
              <input className="input" type="number" value={ageMax} min={0} max={120} onChange={(e) => setAgeMax(+e.target.value)} />
            </div>
          </div>
          <button className="btn btn--primary" style={{ height: 44 }} onClick={onRun} disabled={loading || !copy.trim()}>
            {loading ? "Simulating…" : "Run simulation"}
          </button>
        </div>
        <div className="tiny mut" style={{ marginTop: 16 }}>
          No backend running? Click <strong>▶ Demo</strong> for a full worked example.
        </div>
      </Card>
    </div>
  );
}

/* The four-band full-screen dashboard. */
function Dashboard({ report, rewrite, rwLoading, onRewrite }: { report: Report; rewrite: RewriteResult | null; rwLoading: boolean; onRewrite: () => void }) {
  return (
    <div className="dash">
      {/* Band 1 — L1 metrics */}
      <L1Strip report={report} />

      {/* Band 2 — feel/comments (left, stacked) + campaign highlight WITH inline rewrites (right) */}
      <div className="band band--2">
        <div className="col col--stack">
          <FeelChart report={report} />
          <CommentCloud report={report} />
        </div>
        <div className="col">
          <CampaignHighlight report={report} rewrite={rewrite} rwLoading={rwLoading} onRewrite={onRewrite} />
        </div>
      </div>

      {/* Band 3 — personas positive / negative */}
      <div className="band-title">Personas</div>
      <PersonaBoards report={report} />

      {/* Band 4 — top row: region · target audience · risk anatomy */}
      <div className="band-title">Regional & comparative</div>
      <div className="band band--3">
        <IndiaHeatmap report={report} />
        <TargetVenn report={report} />
        <RiskAnatomyRadar report={report} />
      </div>
      {/* Band 4 — below: comparison table, full width */}
      <CampaignComparison report={report} />
    </div>
  );
}
