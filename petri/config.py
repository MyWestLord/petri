from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class Thresholds:
    max_bundle_pct: float = 15.0        # % of supply bought inside the launch window by linked wallets
    max_sniper_pct: float = 12.0        # % of supply bought in the first ~slot
    max_top10_pct: float = 35.0         # excl. bonding curve / AMM
    max_cluster_pct: float = 20.0       # bubblemap-style funder clusters
    min_organic_kols: int = 2
    min_curve_pct: float = 8.0
    max_curve_pct: float = 92.0


@dataclass
class Exits:
    size_sol: float = 1.5
    tp_ladder: list[tuple[float, float]] = field(default_factory=lambda: [(1.0, 0.4), (3.0, 0.4)])  # (+100% sell 40%), (+300% sell 40%)
    trailing_runner_pct: float = 20.0
    stop_loss_pct: float = 35.0


@dataclass
class Config:
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    live: bool = False                  # paper trading unless explicitly enabled
    private_key_b58: str | None = None
    x_bearer: str | None = None
    db_path: str = "petri_memory.sqlite"
    thresholds: Thresholds = field(default_factory=Thresholds)
    exits: Exits = field(default_factory=Exits)

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        raw: dict = {}
        if path and os.path.exists(path):
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
        c = cls(
            rpc_url=os.getenv("PETRI_RPC_URL", raw.get("rpc_url", cls.rpc_url)),
            live=os.getenv("PETRI_LIVE", str(raw.get("live", False))).lower() in ("1", "true", "yes"),
            private_key_b58=os.getenv("PETRI_PRIVATE_KEY"),
            x_bearer=os.getenv("PETRI_X_BEARER"),
            db_path=raw.get("db_path", cls.db_path),
            thresholds=Thresholds(**raw.get("thresholds", {})),
            exits=Exits(**{k: (v if k != "tp_ladder" else [tuple(x) for x in v]) for k, v in raw.get("exits", {}).items()}),
        )
        if c.live and not c.private_key_b58:
            raise SystemExit("PETRI_LIVE=1 needs PETRI_PRIVATE_KEY. Refusing to start. (Use a burner wallet.)")
        return c
