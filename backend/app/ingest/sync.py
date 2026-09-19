"""Ingest pipeline and scheduler.

    sources -> backlash filter -> sandbox body fetch -> classify -> corpus -> cohort

Runs on an interval inside the FastAPI process. No external cron, no extra
infrastructure; the scheduler starts and stops with the app and is controllable
over the API.

**Why the filter is tight.** Marketing feeds are overwhelmingly product launches,
hires, and agency wins. A permissive filter fills the corpus with press releases,
and a corpus of noise is worse than an empty one: the comparison panels would
confidently match a marketer's copy against an unrelated launch announcement.
Requiring both a campaign signal and a backlash signal keeps precision high at
the cost of recall, which is the right trade here.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.corpus.store import (
    CorpusStore,
    Incident,
    classify_kind,
    cohort_incidents,
    extract_brand,
    looks_like_backlash,
)
from app.ingest.sandbox import ArticleSandbox
from app.ingest.sources import ApifySource, GDELTSource, RawArticle, RSSSource

logger = logging.getLogger(__name__)


@dataclass
class SyncReport:
    started_at: str
    finished_at: str = ""
    fetched: int = 0
    by_provider: dict[str, int] = field(default_factory=dict)
    passed_filter: int = 0
    bodies_fetched: int = 0
    added: int = 0
    duplicates: int = 0
    cohorts: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "fetched": self.fetched,
            "by_provider": self.by_provider,
            "passed_filter": self.passed_filter,
            "bodies_fetched": self.bodies_fetched,
            "added": self.added,
            "duplicates": self.duplicates,
            "cohorts": self.cohorts,
            "errors": self.errors,
        }


def _incident_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def to_incident(article: RawArticle, confidence: float) -> Incident:
    text = f"{article.title} {article.summary} {article.body[:3000]}"
    kind, kind_conf = classify_kind(text)

    return Incident(
        id=_incident_id(article.url),
        title=article.title,
        url=article.url,
        source=article.source,
        published=article.published,
        kind=kind,
        brand=extract_brand(article.title),
        summary=(article.summary or article.body[:400]).strip(),
        # Mined outcomes are journalist narrative, never a measured result. The
        # label confidence blends how clearly this reads as backlash with how
        # cleanly it classified.
        outcome="Reported backlash — outcome not independently verified.",
        label_source="mined",
        label_confidence=round(min(1.0, 0.6 * confidence + 0.4 * kind_conf), 3),
        ingested_at=datetime.now(UTC).isoformat(),
    )


class IngestPipeline:
    """One sync cycle: fetch, filter, enrich, store, cohort."""

    def __init__(
        self,
        store: CorpusStore | None = None,
        apify_token: str | None = None,
        fetch_bodies: bool = True,
        max_bodies: int = 20,
    ) -> None:
        self.store = store or CorpusStore()
        self.gdelt = GDELTSource()
        self.rss = RSSSource()
        self.apify = ApifySource(token=apify_token)
        self.sandbox = ArticleSandbox()
        self.fetch_bodies = fetch_bodies
        self.max_bodies = max_bodies

    @property
    def enabled_sources(self) -> list[str]:
        names = ["gdelt", "rss"]
        if self.apify.enabled:
            names.append("apify")
        return names

    async def run(self, window_days: int = 7) -> SyncReport:
        report = SyncReport(started_at=datetime.now(UTC).isoformat())

        # --- fetch from every configured source, concurrently ---
        tasks = [
            self.gdelt.fetch(window_days=window_days),
            self.rss.fetch(window_days=window_days),
        ]
        if self.apify.enabled:
            tasks.append(self.apify.fetch(window_days=window_days))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[RawArticle] = []
        for res in results:
            if isinstance(res, BaseException):
                report.errors.append(f"{type(res).__name__}: {res}")
                continue
            articles.extend(res)

        report.fetched = len(articles)
        for a in articles:
            report.by_provider[a.provider] = report.by_provider.get(a.provider, 0) + 1

        # --- filter to things that actually look like campaign failures ---
        known = self.store.urls()
        candidates: list[tuple[RawArticle, float]] = []
        for a in articles:
            if not a.url or a.url in known:
                report.duplicates += 1
                continue
            is_backlash, conf = looks_like_backlash(a.title, a.summary, a.body)
            if is_backlash:
                candidates.append((a, conf))

        report.passed_filter = len(candidates)
        logger.info(
            "Ingest: %d fetched -> %d passed the backlash filter", len(articles), len(candidates)
        )

        # --- fetch bodies for the strongest candidates ---
        if self.fetch_bodies and candidates:
            top = sorted(candidates, key=lambda c: c[1], reverse=True)[: self.max_bodies]
            fetches = await self.sandbox.fetch_many([a.url for a, _ in top])
            for (article, _), fetched in zip(top, fetches, strict=True):
                if fetched.ok and fetched.body:
                    article.body = fetched.body
                    report.bodies_fetched += 1

        # --- store and cohort ---
        incidents = [to_incident(a, conf) for a, conf in candidates]
        report.added = self.store.add(incidents)

        if report.added:
            all_incidents = cohort_incidents(self.store.load())
            self.store.replace_all(all_incidents)
            report.cohorts = len({i.cohort_id for i in all_incidents if i.cohort_id})

        report.finished_at = datetime.now(UTC).isoformat()
        return report


class SyncScheduler:
    """In-process interval scheduler.

    An asyncio task rather than APScheduler: one dependency fewer, and the
    behaviour needed here is a loop with a sleep. Starts and stops with the app
    lifespan, and an individual cycle failing never kills the loop.
    """

    def __init__(self, pipeline: IngestPipeline, interval_hours: float = 6.0) -> None:
        self.pipeline = pipeline
        self.interval_hours = interval_hours
        self._task: asyncio.Task | None = None
        self._running = False
        self.last_report: SyncReport | None = None
        self.run_count = 0

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def _loop(self) -> None:
        # Delay the first run so startup is not blocked by network I/O.
        await asyncio.sleep(30)
        while self._running:
            try:
                self.last_report = await self.pipeline.run()
                self.run_count += 1
                logger.info(
                    "Scheduled sync #%d: %d added, %d cohorts",
                    self.run_count,
                    self.last_report.added,
                    self.last_report.cohorts,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - a failed cycle must not stop the loop
                logger.exception("Scheduled sync failed: %s", exc)

            await asyncio.sleep(self.interval_hours * 3600)

    def start(self) -> None:
        if self.is_running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Sync scheduler started (every %.1fh)", self.interval_hours)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("Sync scheduler stopped")

    def status(self) -> dict[str, Any]:
        return {
            "running": self.is_running,
            "interval_hours": self.interval_hours,
            "run_count": self.run_count,
            "sources": self.pipeline.enabled_sources,
            "apify_enabled": self.pipeline.apify.enabled,
            "last_report": self.last_report.as_dict() if self.last_report else None,
        }
