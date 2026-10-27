"""PREFRONTAL — the decision. Counts spikes, respects vetoes, sizes the position."""
from __future__ import annotations

from dataclasses import dataclass

from ..bus import Spike


@dataclass
class Decision:
    action: str      # "BUY" | "ZAP" | "SKIP"
    reason: str
    size_sol: float = 0.0
    fired: int = 0
    total: int = 0


class Prefrontal:
    name = "PREFRONTAL"

    def __init__(self, size_sol: float) -> None:
        self.size_sol = size_sol

    def decide(self, spikes: list[Spike]) -> Decision:
        vetoes = [s for s in spikes if s.verdict == "veto"]
        if vetoes:  # one red flag is enough. no exceptions.
            return Decision("ZAP", ", ".join(f"{v.check}: {v.detail}" for v in vetoes), fired=0, total=len(spikes))
        warns = [s for s in spikes if s.verdict == "warn"]
        fired = len(spikes) - len(warns)
        if warns and fired / max(1, len(spikes)) < 0.85:
            return Decision("SKIP", ", ".join(w.check for w in warns), fired=fired, total=len(spikes))
        size = self.size_sol * (0.5 if warns else 1.0)
        return Decision("BUY", "SPIKE → all regions fired", size_sol=size, fired=fired, total=len(spikes))
