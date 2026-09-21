/* Shared primitives — Card, Chip, Pill, Gauge, etc. The building blocks the
   reference builds everything from: borderless rounded cards, pill controls,
   one rationed lime accent. */

import type { ReactNode } from "react";
import { BAND_COLOR, type Band, type Interval } from "../lib/api";

export function Card({
  title,
  action,
  raised,
  inverted,
  children,
  span,
  className = "",
}: {
  title?: ReactNode;
  action?: ReactNode;
  raised?: boolean;
  inverted?: boolean;
  children: ReactNode;
  span?: number;
  className?: string;
}) {
  const cls = ["card", raised ? "card--raised" : "", inverted ? "card--inverted" : "", className]
    .filter(Boolean)
    .join(" ");
  return (
    <section className={cls} style={span ? { gridColumn: `span ${span}` } : undefined}>
      {(title || action) && (
        <header className="card__head">
          {title && <h4 className="card__title">{title}</h4>}
          {action && <div className="card__action">{action}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Chip({
  children,
  color,
  tone = "neutral",
}: {
  children: ReactNode;
  color?: string;
  tone?: "neutral" | "accent" | "band";
}) {
  const style =
    tone === "band" && color
      ? { background: color, color: "var(--ink)" }
      : tone === "accent"
      ? { background: "var(--lime)", color: "var(--on-accent, var(--ink))" }
      : undefined;
  return (
    <span className={`chip chip--${tone}`} style={style}>
      {children}
    </span>
  );
}

export function BandChip({ band }: { band: Band }) {
  return (
    <span className="chip chip--band tabular" style={{ background: BAND_COLOR[band], color: "var(--ink)" }}>
      {band}
    </span>
  );
}

/* The score gauge. The interval is drawn as a band, never hidden — a product
   requirement, not a style choice. */
export function ScoreGauge({ value, band, interval }: { value: number; band: Band; interval: Interval }) {
  const pct = (n: number) => Math.max(0, Math.min(100, n));
  return (
    <div className="gauge">
      <div className="gauge__value tabular">{value.toFixed(0)}</div>
      <div className="gauge__band">
        <BandChip band={band} />
      </div>
      <div className="gauge__track" aria-label={`Risk index ${value}, interval ${interval.lower} to ${interval.upper}`}>
        <div
          className="gauge__interval"
          style={{ left: `${pct(interval.lower)}%`, width: `${pct(interval.upper) - pct(interval.lower)}%` }}
        />
        <div className="gauge__marker" style={{ left: `${pct(value)}%`, background: BAND_COLOR[band] }} />
      </div>
      <div className="gauge__ci tabular">
        CI₈₀ [{interval.lower.toFixed(0)} — {interval.upper.toFixed(0)}] · {interval.persona_count} personas
      </div>
      {interval.is_wide && (
        <div className="gauge__split">⚠ Your audience is split on this — personas disagree sharply.</div>
      )}
    </div>
  );
}

/* Horizontal bar meter used across risk anatomy, alignment, etc. */
export function Meter({ value, max = 1, color = "var(--ink)", label }: { value: number; max?: number; color?: string; label?: ReactNode }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="meter">
      {label && <div className="meter__label">{label}</div>}
      <div className="meter__track">
        <div className="meter__fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export function IconButton({ children, onClick, active, title }: { children: ReactNode; onClick?: () => void; active?: boolean; title?: string }) {
  return (
    <button className={`iconbtn ${active ? "iconbtn--active" : ""}`} onClick={onClick} title={title} aria-label={title}>
      {children}
    </button>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

const EMOTION_COLOR: Record<string, string> = {
  positive: "var(--lime)",
  amused: "var(--lime-pale)",
  curious: "var(--cat-3)",
  neutral: "var(--cat-7)",
  confused: "var(--cat-5)",
  uncomfortable: "var(--band-high)",
  offended: "var(--band-severe)",
};

export function emotionColor(e: string) {
  return EMOTION_COLOR[e] || "var(--cat-7)";
}
