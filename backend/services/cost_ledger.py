"""
Lightweight monthly cost ledger for LLM API spend.

EchoFrame's CLAUDE.md sets a hard $50/month ceiling on Anthropic spend
across all reports and pipelines, motivated by an April 2026 incident
where unbounded LLM loops burned ~$150 in a single session. This
module is the budget gatekeeper: every caller checks `can_spend(usd)`
before making an LLM request and records `record_spend(usd)` after.

The ledger is JSON-file-backed and is intentionally simple — no
database, no Redis, no per-user partitioning. The single counter is
month-bucketed so a new month resets the budget without manual
intervention.

Failure mode: when the ceiling is reached, `can_spend` returns False
and callers must degrade gracefully (skip the LLM call, ship a
deterministic alternative). Never silently retry or queue work.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


# Default hard ceiling. Can be overridden via env LLM_COST_CEILING_USD.
_DEFAULT_CEILING_USD: float = 50.0

# The ledger lives next to the diagnostics dir so it persists across
# Render deploys when the same disk is reused; on free-tier instances
# the disk is ephemeral and the ledger naturally resets on each restart.
_LEDGER_PATH = (
    Path(__file__).resolve().parent.parent / "models" / "diagnostics" / "llm_cost_ledger.json"
)


def _month_key(when: Optional[datetime] = None) -> str:
    """Return the YYYY-MM bucket key for the given moment (UTC)."""
    when = when or datetime.now(tz=timezone.utc)
    return when.strftime("%Y-%m")


class CostLedger:
    """File-backed monthly LLM cost counter with a hard ceiling."""

    _lock = threading.Lock()

    def __init__(
        self,
        ceiling_usd: Optional[float] = None,
        path: Optional[Path] = None,
    ) -> None:
        env_ceiling = os.environ.get("LLM_COST_CEILING_USD")
        if ceiling_usd is None and env_ceiling:
            try:
                ceiling_usd = float(env_ceiling)
            except ValueError:
                logger.warning("Invalid LLM_COST_CEILING_USD=%r; using default", env_ceiling)
        self.ceiling_usd: float = ceiling_usd if ceiling_usd is not None else _DEFAULT_CEILING_USD
        self.path: Path = path or _LEDGER_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cost ledger read failed (%s); treating as empty", exc)
            return {}

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            tmp.replace(self.path)
        except OSError as exc:
            logger.warning("Cost ledger write failed (%s); spend may be untracked", exc)

    def current_spend_usd(self, when: Optional[datetime] = None) -> float:
        """Return total USD spent in the current UTC month."""
        with self._lock:
            data = self._read()
        return float(data.get(_month_key(when), 0.0))

    def can_spend(self, projected_usd: float, when: Optional[datetime] = None) -> bool:
        """
        Return True iff spending an additional `projected_usd` would
        keep the month total at or below the ceiling. Callers must
        check this BEFORE making the LLM call.
        """
        if projected_usd <= 0:
            return True
        return (self.current_spend_usd(when) + projected_usd) <= self.ceiling_usd

    def record_spend(self, actual_usd: float, when: Optional[datetime] = None) -> float:
        """
        Accumulate the spend into the current month's bucket. Returns
        the new month total. Safe to call from concurrent requests on
        the same process; cross-process safety is not guaranteed but
        the budget is approximate, not financial-accounting precise.
        """
        if actual_usd <= 0:
            return self.current_spend_usd(when)
        with self._lock:
            data = self._read()
            key = _month_key(when)
            data[key] = float(data.get(key, 0.0)) + float(actual_usd)
            self._write(data)
            return data[key]

    def headroom_usd(self, when: Optional[datetime] = None) -> float:
        """Remaining budget for the current UTC month."""
        return max(0.0, self.ceiling_usd - self.current_spend_usd(when))


# Process-wide singleton — every LLM caller imports `get_cost_ledger()`.
_default: Optional[CostLedger] = None


def get_cost_ledger() -> CostLedger:
    global _default
    if _default is None:
        _default = CostLedger()
    return _default
