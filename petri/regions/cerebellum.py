"""CEREBELLUM — timing. Take-profit ladder, trailing runner, stop loss."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Exits


@dataclass
class Position:
    mint: str
    symbol: str
    entry_price: float
    size_sol: float
    remaining: float = 1.0          # fraction of the bag still held
    peak: float = 0.0
    hit: set[int] = field(default_factory=set)


class Cerebellum:
    name = "CEREBELLUM"

    def __init__(self, ex: Exits) -> None:
        self.ex = ex

    def step(self, pos: Position, price: float) -> list[tuple[str, float]]:
        """Return a list of (reason, fraction_of_original_bag_to_sell)."""
        orders: list[tuple[str, float]] = []
        gain = price / pos.entry_price - 1
        pos.peak = max(pos.peak, price)
        if gain <= -self.ex.stop_loss_pct / 100 and pos.remaining > 0:
            orders.append(("SL", pos.remaining))
            return orders
        for i, (tp, frac) in enumerate(self.ex.tp_ladder):
            if gain >= tp and i not in pos.hit and pos.remaining > 0:
                pos.hit.add(i)
                orders.append((f"TP{i + 1}", min(frac, pos.remaining)))
        if len(pos.hit) == len(self.ex.tp_ladder) and pos.remaining > 0:
            if price <= pos.peak * (1 - self.ex.trailing_runner_pct / 100):
                orders.append(("runner", pos.remaining))
        return orders
