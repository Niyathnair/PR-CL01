"""Application settings.

Model choices follow the plan (§18.2): Sonnet for the persona fan-out, where
cost-per-call dominates because we make 11-30 of them; Opus for the once-per-run
synthesis work that needs stronger reasoning; Haiku for cheap triage.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CROWDLENS_", env_file=".env", extra="ignore")

    # --- models (§18.2) ---
    persona_model: str = "claude-sonnet-5"
    synthesis_model: str = "claude-opus-5"
    triage_model: str = "claude-haiku-4-5-20251001"

    # --- sampling ---
    # Low but non-zero: personas need enough variance to produce a meaningful
    # spread for the bootstrap (§13), but not so much that re-runs disagree
    # with themselves (§19.3 asserts stability within 5 index points).
    persona_temperature: float = 0.3
    max_tokens_persona: int = 2000
    max_tokens_synthesis: int = 4000

    # --- orchestration ---
    max_concurrency: int = 12
    call_timeout_seconds: float = 90.0
    max_retries: int = 3

    # --- selection (§6) ---
    target_k: int = 11
    adversarial_slots: int = 3
    diversity_mu: float = 0.3

    # --- scoring weights (§9.3) ---
    # Priors to be calibrated against the golden set, NOT validated constants.
    # gamma is largest by design: for reputational risk the tail matters more
    # than the average.
    weight_alpha: float = 0.30  # offense mass
    weight_beta: float = 0.25  # amplification
    weight_gamma: float = 0.35  # tail risk
    weight_delta: float = 0.10  # ambiguity

    # --- override rule (§9.4) ---
    override_severity: float = 0.90
    override_confidence: float = 0.70

    # --- uncertainty (§13) ---
    bootstrap_iterations: int = 1000
    ci_lower_quantile: float = 0.10
    ci_upper_quantile: float = 0.90

    # --- ingest (§5.5) ---
    # Apify is optional: it supplies social reaction volume via managed actors,
    # so no personal account or session cookie is ever involved. Without a token
    # the pipeline runs on GDELT + RSS, which are free and need no auth.
    apify_token: str = ""
    apify_actor: str = "apidojo~tweet-scraper"
    sync_interval_hours: float = 6.0
    sync_on_startup: bool = False
    sync_window_days: int = 7

    # --- clustering (§11.1) ---
    cluster_distance_threshold: float = 0.35

    # --- risk matrix (§12.1) ---
    risk_flag_threshold: float = 0.30


settings = Settings()
