"""HTTP API. Everything the engine computes is exposed here — there is no UI.

Panel endpoints exist so a client can fetch one analysis without re-running the
simulation: ``POST /v1/simulate`` once, then ``GET /v1/runs/{id}/panels/{name}``
as many times as needed.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.context.provider import list_scenarios
from app.llm.auth import describe_credential
from app.orchestrator.run import build_report, execute_run
from app.personas.registry import get_registry, reload_registry
from app.rewrite.engine import rewrite_and_rescore
from app.store import RunStore

logger = logging.getLogger(__name__)
router = APIRouter()


class SimulateRequest(BaseModel):
    # Named `text` rather than `copy` because `copy` shadows BaseModel.copy.
    text: str = Field(
        min_length=1,
        max_length=8000,
        description="The marketing copy to test",
        alias="copy",
        validation_alias="copy",
        serialization_alias="copy",
    )
    brand_intent: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            "What the brand means to say. Required for a meaningful Intent Alignment "
            "Score — without it, interpretation gap cannot be measured."
        ),
    )
    context_scenario: str = Field(default="quiet", description="Context fixture to simulate under")
    k: int | None = Field(default=None, ge=2, le=40, description="Persona count override")
    enable_composites: bool = Field(
        default=True, description="Run Tier-2 blind-spot discovery (never affects the score)"
    )

    model_config = {"populate_by_name": True}


class SimulateResponse(BaseModel):
    model_config = {"populate_by_name": True}

    run_id: str
    report: dict[str, Any]


def _store(request: Request) -> RunStore:
    return request.app.state.store


def _runs(request: Request) -> RunStore:
    """Raw RunResult objects, kept so /rewrite can reuse a run's reactions."""
    return request.app.state.runs


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    cred = request.app.state.llm.credential
    registry = get_registry()
    return {
        "status": "ok",
        "anthropic_auth": describe_credential(cred),
        "auth_kind": cred.kind,
        "is_subscription_credential": cred.is_subscription,
        "personas_loaded": len(registry),
        "mandatory_personas": [n.id for n in registry.values() if n.mandatory],
        "context_scenarios": list_scenarios(),
    }


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest, request: Request) -> SimulateResponse:
    """Run a full simulation. This is the one expensive call; panels are free after."""
    registry = get_registry()
    try:
        result = await execute_run(
            client=request.app.state.llm,
            registry=registry,
            copy=req.text,
            brand_intent=req.brand_intent,
            context_scenario=req.context_scenario,
            k=req.k,
            enable_composites=req.enable_composites,
        )
    except Exception as exc:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=502, detail=f"Simulation failed: {exc}") from exc

    report = build_report(result, registry)
    _store(request).put(result.run_id, report)
    _runs(request).put(result.run_id, result)
    return SimulateResponse(run_id=result.run_id, report=report)


class RewriteRequest(BaseModel):
    constraints: str | None = Field(
        default=None,
        max_length=1000,
        description="Hard constraints: character limits, mandatory claims, required legal language",
    )


@router.post("/runs/{run_id}/rewrite")
async def rewrite(run_id: str, req: RewriteRequest, request: Request) -> dict[str, Any]:
    """Generate three variants and re-score each one.

    Improvements are demonstrated, not claimed: every variant goes back through
    the personas that flagged the original, plus controls to catch a rewrite
    that fixes one problem and creates another.
    """
    result = _runs(request).get(run_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found or expired. Re-run POST /v1/simulate.",
        )

    registry = get_registry()
    try:
        return await rewrite_and_rescore(
            client=request.app.state.llm,
            result=result,
            registry=registry,
            constraints=req.constraints,
        )
    except Exception as exc:
        logger.exception("Rewrite failed")
        raise HTTPException(status_code=502, detail=f"Rewrite failed: {exc}") from exc


@router.get("/runs")
async def list_runs(request: Request, limit: int = 20) -> dict[str, Any]:
    return {"runs": _store(request).list(limit)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> dict[str, Any]:
    report = _store(request).get(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return report


# Panel name -> path into the report. Lets a client pull one analysis cheaply.
_PANEL_PATHS: dict[str, tuple[str, ...]] = {
    "risk_index": ("risk_index",),
    "intent_alignment": ("intent_alignment",),
    "intent_vs_interpretation": ("understanding", "intent_vs_interpretation"),
    "intent_alignment_breakdown": ("understanding", "intent_alignment_breakdown"),
    "what_they_think_youre_saying": ("understanding", "what_they_think_youre_saying"),
    "backlash_pathway": ("cause", "backlash_pathway"),
    "emotional_response": ("feeling", "emotional_response"),
    "persona_reactions": ("feeling", "persona_reactions"),
    "simulated_comments": ("feeling", "simulated_comments"),
    "why_risky": ("risk", "why_risky"),
    "risk_anatomy": ("risk", "risk_anatomy"),
    "severity_likelihood": ("risk", "severity_likelihood"),
    "controversial_vs_misunderstood": ("risk", "controversial_vs_misunderstood"),
    "audience_heatmap": ("who", "audience_heatmap"),
    "region_heatmap": ("who", "region_heatmap"),
    "target_vs_unintended": ("who", "target_vs_unintended"),
    "who_might_misunderstand": ("who", "who_might_misunderstand"),
    "trigger_index": ("cause", "trigger_index"),
    "meme_potential": ("cause", "meme_potential"),
    "blind_spot_findings": ("blind_spot_findings",),
    "severe_discovery_alert": ("severe_discovery_alert",),
    "selection": ("selection",),
    "context": ("context",),
    "usage": ("usage",),
}


@router.get("/panels")
async def list_panels() -> dict[str, Any]:
    return {"panels": sorted(_PANEL_PATHS)}


@router.get("/runs/{run_id}/panels/{panel}")
async def get_panel(run_id: str, panel: str, request: Request) -> dict[str, Any]:
    report = _store(request).get(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    path = _PANEL_PATHS.get(panel)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown panel {panel!r}. Available: {', '.join(sorted(_PANEL_PATHS))}",
        )

    node: Any = report
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return {"run_id": run_id, "panel": panel, "data": node}


@router.get("/personas")
async def list_personas() -> dict[str, Any]:
    registry = get_registry()
    return {
        "count": len(registry),
        "personas": [
            {
                "id": n.id,
                "version": n.version,
                "label": n.label,
                "region": n.demographics.region,
                "audience_type": n.demographics.audience_type,
                "prevalence_weight": n.prevalence_weight,
                "vocality": n.vocality,
                "is_target": n.is_target,
                "mandatory": n.mandatory,
                "is_control": n.is_control,
                "sensitivity_profile": n.sensitivity_profile.model_dump(),
            }
            for n in sorted(registry.values(), key=lambda x: x.id)
        ],
    }


@router.get("/personas/{persona_id}")
async def get_persona(persona_id: str) -> dict[str, Any]:
    node = get_registry().get(persona_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    return node.model_dump()


@router.post("/personas/reload")
async def reload_personas() -> dict[str, Any]:
    registry = reload_registry()
    return {"reloaded": True, "count": len(registry)}


@router.get("/scenarios")
async def scenarios() -> dict[str, Any]:
    return {"scenarios": list_scenarios()}
