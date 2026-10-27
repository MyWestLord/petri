"""VISUAL — reads the bonding curve, holder concentration and the chart (DexScreener)."""
from __future__ import annotations

import httpx

from ..bus import Spike, Stimulus
from ..config import Thresholds
from ..feeds.dexscreener import best_pair
from ..feeds.solana_rpc import RPC

PUMP_SUPPLY = 1_000_000_000
CURVE_START_VSOL = 30.0   # virtual SOL at launch
CURVE_END_VSOL = 115.0    # approx. graduation point (check current pump.fun params)


class Visual:
    name = "VISUAL"

    def __init__(self, rpc: RPC, http: httpx.AsyncClient, th: Thresholds) -> None:
        self.rpc, self.http, self.th = rpc, http, th

    def curve(self, s: Stimulus, trades: list[dict]) -> Spike:
        v = None
        for t in reversed(trades):
            if t.get("vSolInBondingCurve"):
                v = float(t["vSolInBondingCurve"])
                break
        v = v or float(s.meta.get("v_sol") or CURVE_START_VSOL)
        pct = max(0.0, min(100.0, 100 * (v - CURVE_START_VSOL) / (CURVE_END_VSOL - CURVE_START_VSOL)))
        s.curve_pct = pct
        ok = self.th.min_curve_pct <= pct <= self.th.max_curve_pct
        return Spike(self.name, "bonding.curve", "ok" if ok else "warn", f"{pct:.0f}%", pct / 100)

    async def top10(self, s: Stimulus) -> Spike:
        holders = await self.rpc.largest_holders(s.mint)
        # #1 is usually the bonding curve / AMM vault — skip it
        share = 100 * sum(float(h.get("uiAmount") or 0) for h in holders[1:11]) / PUMP_SUPPLY
        return Spike(self.name, "top10.share", "veto" if share > self.th.max_top10_pct else "ok", f"{share:.0f}%", share / 100)

    async def chart(self, s: Stimulus) -> Spike:
        p = await best_pair(self.http, s.mint)
        if not p:
            return Spike(self.name, "dexscreener", "ok", "not listed yet (still on curve)", 0.0)
        vol5 = (p.get("volume") or {}).get("m5", 0)
        chg5 = (p.get("priceChange") or {}).get("m5", 0)
        return Spike(self.name, "dexscreener", "warn" if chg5 < -40 else "ok", f"5m vol ${vol5:,.0f} · {chg5:+.0f}%", 0.5)
