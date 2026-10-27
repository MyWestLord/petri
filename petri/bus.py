"""Spikes: the messages neurons (regions) fire at each other."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

Verdict = Literal["ok", "warn", "veto"]


@dataclass
class Stimulus:
    """A new coin entering the dish."""
    mint: str
    symbol: str
    name: str
    dev: str
    source: str  # "pump" | "dex"
    created_at: float
    market_cap_sol: float = 0.0
    curve_pct: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Spike:
    """One region's opinion about one stimulus."""
    region: str
    check: str
    verdict: Verdict
    detail: str
    score: float = 0.0  # 0..1, how sure the region is


class Bus:
    """Tiny async pub/sub. Every region hears every spike — mycelium, but neurons."""

    def __init__(self) -> None:
        self._subs: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.append(q)
        return q

    def fire(self, event: Any) -> None:
        for q in self._subs:
            q.put_nowait(event)
