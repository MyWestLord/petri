"""DOPAMINE — the reward loop. Tracks PnL per check so the brain learns which signals pay."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Dopamine:
    realized_sol: float = 0.0
    wins: int = 0
    losses: int = 0
    zaps: int = 0
    signal_pnl: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    def reward(self, pnl_sol: float, checks: list[str]) -> None:
        self.realized_sol += pnl_sol
        if pnl_sol >= 0:
            self.wins += 1
        else:
            self.losses += 1
        for c in checks:
            self.signal_pnl[c] += pnl_sol

    def pain(self) -> None:
        """A rug got zapped before entry. The brain hates chaos — log it."""
        self.zaps += 1
