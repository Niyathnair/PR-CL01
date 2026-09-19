/* API client. Types mirror the backend's build_report() shape exactly. */

export type Band = "Clear" | "Low" | "Elevated" | "High" | "Severe";

export interface Interval {
  point: number;
  lower: number;
  upper: number;
  width: number;
  persona_count: number;
  is_wide: boolean;
}

export interface RiskIndex {
  value: number;
  band: Band;
  interval: Interval;
  components: {
    offense_mass: number;
    amplification: number;
    tail_risk: number;
    ambiguity: number;
    context_multiplier: number;
    raw: number;
  };
  override_fired: boolean;
  override_persona_id: string | null;
  label: string;
  disclaimer: string;
}

export interface Trigger {
  span: string;
  char_start: number;
  char_end: number;
  modality: string;
  why: string;
  valence: string;
}

export interface PersonaReaction {
  persona_id: string;
  label: string;
  region: string | null;
  severity: number;
  confidence: number;
  emotion: string;
  emotion_intensity: number;
  sentiment: string;
  comprehension: string;
  intent_alignment: number;
  paraphrase: string;
  perceived_intent: string;
  likely_behavior: string;
  likely_comment: { text: string; tone: string };
  charitable_reading: string;
  hostile_reading: string;
  triggers: Trigger[];
  prevalence_weight: number;
}

export interface Report {
  run_id: string;
  created_at: string;
  copy: string;
  brand_intent: string | null;
  risk_index: RiskIndex;
  intent_alignment: { value: number; label: string };
  l1_metrics: L1Metric[];
  geo_india: {
    available: boolean;
    note: string;
    states: Array<{ code: string; name: string; intensity: number; tone: "negative" | "positive" | "neutral" }>;
  };
  target_venn: {
    available: boolean;
    reason?: string;
    target_age?: [number, number];
    target_share?: number;
    buckets?: Record<string, number>;
    note?: string;
  };
  campaign_comparison: {
    available: boolean;
    this_campaign: { risk_dimensions: Record<string, number> };
    matches: Array<{
      similarity: number;
      title: string;
      url: string;
      source: string;
      published: string;
      kind: string;
      brand: string | null;
      cohort_id: string | null;
      label_source: string;
      label_confidence: number;
      is_reliable: boolean;
      caveat: string | null;
      outcome?: string;
      scores?: Record<string, number>;
    }>;
    caveat: string;
  };
  understanding: {
    intent_vs_interpretation: Array<{
      persona_id: string;
      label: string;
      perceived_intent: string;
      paraphrase: string;
      gap: number;
      comprehension: string;
    }>;
    what_they_think_youre_saying: Array<{
      label: string;
      label_from_persona: string;
      personas: string[];
      audience_mass: number;
      size: number;
      share: number;
    }>;
    intent_alignment_breakdown: Array<{
      persona_id: string;
      intent_alignment: number;
      comprehension: string;
      perceived_intent: string;
    }>;
  };
  feeling: {
    emotional_response: {
      distribution: Record<string, number>;
      by_persona: Array<{ persona_id: string; emotion: string; intensity: number }>;
      polarization: number;
    };
    persona_reactions: PersonaReaction[];
    simulated_comments: Array<{
      persona_id: string;
      label: string;
      text: string;
      tone: string;
      emotion: string;
      weight: number;
      behavior: string;
    }>;
  };
  risk: {
    why_risky: Record<string, Array<{ span: string; why: string; valence: string; persona_id: string; severity: number }>>;
    risk_anatomy: Record<string, number>;
    severity_likelihood: Array<{
      dimension: string;
      likelihood: number;
      severity: number;
      affected_personas: string[];
      quadrant: string;
    }>;
    controversial_vs_misunderstood: {
      points: Array<{ persona_id: string; comprehension: number; opposition: number; quadrant: string; weight: number }>;
      mass: Record<string, number>;
      prescriptions: Record<string, string>;
    };
  };
  who: {
    audience_heatmap: { facet: string; cells: Array<{ persona_id: string; label: string; facet: string; emotion: string; intensity: number; severity: number; weight: number }> };
    region_heatmap: Array<{ region: string; mean_severity: number; mean_intent_alignment: number; persona_count: number; personas: string[]; dominant_emotion: string }>;
    target_vs_unintended: {
      target: Record<string, unknown>;
      unintended: Record<string, unknown>;
      severity_gap: number | null;
    };
    who_might_misunderstand: Array<{ persona_id: string; label: string; comprehension: string; gap: number; they_think_you_said: string; triggers: string[] }>;
  };
  cause: {
    trigger_index: Array<{ span: string; char_start: number; char_end: number; modality: string; personas: Array<{ persona_id: string; why: string; valence: string; severity: number }>; max_severity: number; audience_mass: number; persona_count: number }>;
    meme_potential: { score: number; would_share_mocking: string[]; mocking_audience_mass: number; candidate_spans: Array<{ span: string; char_start: number; char_end: number; persona_id: string; meme_potential: number; why: string }> };
    backlash_pathway: {
      nodes: Array<{ id: string; stage: string; label: string; detail: string; grounded_in: string[]; evidence: string; audience_mass: number; severity: number }>;
      edges: Array<{ source: string; target: string; likelihood: number; basis: string }>;
      terminated_at: string | null;
      termination_reason: string | null;
      overall_likelihood: number;
      grounding_note: string;
    };
  };
  blind_spot_findings: Array<{ composite_id: string; severity: number; confidence: number; emotion: string; paraphrase: string; comment: string; triggers: Trigger[]; not_scored: boolean; disclaimer: string }>;
  severe_discovery_alert: { composite_id: string; severity: number; confidence: number; reaction: string; comment: string; affects_score: boolean; message: string } | null;
  selection: {
    selected: Array<{ persona_id: string; label: string; relevance: number; stage: string; reason: string }>;
    activated_axes: Record<string, number>;
    entities: string[];
    topics: string[];
    candidate_pool_size: number;
  };
  context: {
    scenario: string;
    provenance: string;
    provenance_badge: { value: string; is_live: boolean; label: string };
    multiplier?: number;
    items?: Array<{ headline: string; source: string; date: string; stance: string; salience: number }>;
    active_controversies?: string[];
  };
  control_canary: { fired: boolean; severity: number; message: string | null } | null;
  usage: { calls: number; estimated_cost_usd: number; by_model?: Record<string, number> };
}

export interface L1Metric {
  key: string;
  label: string;
  value: number;
  unit: string;
  sub: string;
  tone: "band" | "neutral" | "inverted";
}

export interface SimulateRequest {
  copy: string;
  brand_intent?: string;
  context_scenario?: string;
  enable_composites?: boolean;
  target_age_min?: number;
  target_age_max?: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/v1${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => req<{ status: string; anthropic_auth: string; personas_loaded: number; context_scenarios: string[] }>("/health"),
  scenarios: () => req<{ scenarios: string[] }>("/scenarios"),
  simulate: (body: SimulateRequest) =>
    req<{ run_id: string; report: Report }>("/simulate", { method: "POST", body: JSON.stringify(body) }),
  rewrite: (runId: string, constraints?: string) =>
    req<RewriteResult>(`/runs/${runId}/rewrite`, { method: "POST", body: JSON.stringify({ constraints }) }),
  similar: (copy: string) =>
    req<{ corpus_size: number; matches: SimilarMatch[]; caveat: string }>("/corpus/similar", { method: "POST", body: JSON.stringify({ copy }) }),
};

export interface RewriteVariant {
  kind: string;
  text: string;
  rationale: string;
  preserved: string;
  sacrificed: string;
  risk_index: number;
  band: Band;
  interval: Interval;
  intent_alignment: number;
  resolved_triggers: string[];
  new_triggers: string[];
  improved: boolean;
}

export interface RewriteResult {
  original: { text: string; risk_index: number; band: Band; intent_alignment: number };
  variants: RewriteVariant[];
  best_variant: string | null;
  any_improved: boolean;
  rescored_against: string[];
  note: string | null;
}

export interface SimilarMatch {
  similarity: number;
  title: string;
  url: string;
  source: string;
  published: string;
  kind: string;
  brand: string | null;
  cohort_id: string | null;
  label_source: string;
  label_confidence: number;
  is_reliable: boolean;
  caveat: string | null;
}

export const BAND_COLOR: Record<Band, string> = {
  Clear: "var(--band-clear)",
  Low: "var(--band-low)",
  Elevated: "var(--band-elevated)",
  High: "var(--band-high)",
  Severe: "var(--band-severe)",
};
