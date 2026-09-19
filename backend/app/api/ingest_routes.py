"""Ingest, corpus, and scheduler endpoints."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.corpus.store import cohort_summary, find_similar
from app.ingest.sources import DEFAULT_FEEDS

logger = logging.getLogger(__name__)
router = APIRouter()


def _scheduler(request: Request):
    sched = getattr(request.app.state, "scheduler", None)
    if sched is None:
        raise HTTPException(status_code=503, detail="Ingest scheduler not configured")
    return sched


class SyncRequest(BaseModel):
    window_days: int = Field(default=7, ge=1, le=90)


@router.post("/ingest/sync")
async def trigger_sync(req: SyncRequest, request: Request) -> dict[str, Any]:
    """Run one ingest cycle now, synchronously."""
    sched = _scheduler(request)
    try:
        report = await sched.pipeline.run(window_days=req.window_days)
    except Exception as exc:
        logger.exception("Manual sync failed")
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc
    sched.last_report = report
    return report.as_dict()


@router.get("/ingest/status")
async def ingest_status(request: Request) -> dict[str, Any]:
    return _scheduler(request).status()


@router.post("/ingest/scheduler/start")
async def start_scheduler(request: Request) -> dict[str, Any]:
    sched = _scheduler(request)
    sched.start()
    return {"started": True, "status": sched.status()}


@router.post("/ingest/scheduler/stop")
async def stop_scheduler(request: Request) -> dict[str, Any]:
    sched = _scheduler(request)
    await sched.stop()
    return {"stopped": True}


@router.get("/ingest/feeds/health")
async def feed_health() -> dict[str, Any]:
    """Re-check every configured feed. Feeds rot; this says which are live."""
    results = []
    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={"User-Agent": "crowdLens/0.1 (+research)"},
    ) as client:
        for name, url in DEFAULT_FEEDS.items():
            try:
                resp = await client.get(url)
                is_rss = b"<item" in resp.content or b"<entry" in resp.content
                results.append(
                    {
                        "feed": name,
                        "url": url,
                        "status": resp.status_code,
                        "ok": resp.status_code == 200 and is_rss,
                        "parseable": is_rss,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "feed": name,
                        "url": url,
                        "status": 0,
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    healthy = sum(1 for r in results if r["ok"])
    return {"healthy": healthy, "total": len(results), "feeds": results}


@router.get("/corpus/stats")
async def corpus_stats(request: Request) -> dict[str, Any]:
    return _scheduler(request).pipeline.store.stats()


@router.get("/corpus/incidents")
async def list_incidents(
    request: Request, limit: int = 50, kind: str | None = None
) -> dict[str, Any]:
    incidents = _scheduler(request).pipeline.store.load()
    if kind:
        incidents = [i for i in incidents if i.kind == kind]
    incidents.sort(key=lambda i: i.published, reverse=True)
    return {
        "count": len(incidents),
        "incidents": [i.as_dict() for i in incidents[:limit]],
    }


@router.get("/corpus/cohorts")
async def list_cohorts(request: Request) -> dict[str, Any]:
    incidents = _scheduler(request).pipeline.store.load()
    return {
        "cohorts": cohort_summary(incidents),
        "caveat": (
            "Cohorts built from mined news labels describe what was REPORTED, not "
            "measured outcomes. Check `reliability` before treating one as evidence."
        ),
    }


class SimilarRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=8000,
        alias="copy",
        validation_alias="copy",
        serialization_alias="copy",
    )
    limit: int = Field(default=5, ge=1, le=20)
    model_config = {"populate_by_name": True}


@router.post("/corpus/similar")
async def similar_incidents(req: SimilarRequest, request: Request) -> dict[str, Any]:
    """Historical Campaign Similarity (§16.15): has something like this failed before?"""
    incidents = _scheduler(request).pipeline.store.load()
    matches = find_similar(incidents, req.text, limit=req.limit)
    return {
        "corpus_size": len(incidents),
        "matches": matches,
        "caveat": (
            "Similarity is over reported incidents. A match is a lead to "
            "investigate, not evidence that this copy will fail."
        ),
    }
