"""In-memory run store.

Stage 1 deliberately has no database. Runs live in process memory with an LRU
bound, which is enough to make the panel endpoints work and keeps the repo
runnable with no infrastructure. Postgres arrives in stage 4, where campaign
history and the comparison panels need durable storage anyway.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


class RunStore:
    def __init__(self, max_runs: int = 100) -> None:
        self._runs: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max = max_runs

    def put(self, run_id: str, report: dict[str, Any]) -> None:
        self._runs[run_id] = report
        self._runs.move_to_end(run_id)
        while len(self._runs) > self._max:
            self._runs.popitem(last=False)

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self._runs.get(run_id)

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        out = []
        for run_id, report in reversed(self._runs.items()):
            out.append(
                {
                    "run_id": run_id,
                    "created_at": report.get("created_at"),
                    "copy": (report.get("copy") or "")[:120],
                    "risk_index": report.get("risk_index", {}).get("value"),
                    "band": report.get("risk_index", {}).get("band"),
                    "intent_alignment": report.get("intent_alignment", {}).get("value"),
                }
            )
            if len(out) >= limit:
                break
        return out
