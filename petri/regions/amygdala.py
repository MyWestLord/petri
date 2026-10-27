"""AMYGDALA — fear. Bundles, block-0 snipers, mint/freeze authority, funder clusters. Can veto anything."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from ..bus import Spike, Stimulus
from ..config import Thresholds
from ..feeds.solana_rpc import RPC

PUMP_SUPPLY = 1_000_000_000  # pump.fun tokens mint 1B (6 decimals)
LAUNCH_WINDOW_S = 2.5        # trades this close to creation ≈ "block 0" / bundled


class Amygdala:
    name = "AMYGDALA"

    def __init__(self, rpc: RPC, th: Thresholds) -> None:
        self.rpc, self.th = rpc, th

    async def authorities(self, s: Stimulus) -> list[Spike]:
        info = await self.rpc.mint_info(s.mint)
        out = []
        for key, label in (("mintAuthority", "mint.authority"), ("freezeAuthority", "freeze.authority")):
            live = info.get(key) is not None
            out.append(Spike(self.name, label, "veto" if live else "ok", "LIVE" if live else "revoked", 1.0))
        return out

    def launch_buys(self, s: Stimulus, trades: list[dict]) -> list[Spike]:
        early = [t for t in trades if t.get("txType") == "buy" and t["_t"] - s.created_at <= LAUNCH_WINDOW_S]
        by_wallet: dict[str, float] = defaultdict(float)
        for t in early:
            by_wallet[t["traderPublicKey"]] += float(t.get("tokenAmount", 0))
        snipe_pct = 100 * sum(v for w, v in by_wallet.items() if w != s.dev) / PUMP_SUPPLY
        bundle_wallets = len(by_wallet)
        bundle_pct = 100 * sum(by_wallet.values()) / PUMP_SUPPLY
        return [
            Spike(self.name, "jito.bundle", "veto" if bundle_wallets >= 4 and bundle_pct > self.th.max_bundle_pct else "ok",
                  f"{bundle_wallets} wallets · {bundle_pct:.1f}%", min(1, bundle_pct / 50)),
            Spike(self.name, "snipers.block0", "veto" if snipe_pct > self.th.max_sniper_pct else "ok", f"{snipe_pct:.1f}% supply",
                  min(1, snipe_pct / 40)),
        ]

    async def clusters(self, s: Stimulus) -> list[Spike]:
        """Bubblemaps-style: group top holders by who funded them. Shared funder = one person."""
        holders = (await self.rpc.largest_holders(s.mint))[:15]
        owners = await asyncio.gather(*(self.rpc.token_account_owner(h["address"]) for h in holders), return_exceptions=True)
        funders = await asyncio.gather(*(self.rpc.first_funder(o) for o in owners if isinstance(o, str)), return_exceptions=True)
        groups: dict[str, float] = defaultdict(float)
        for h, f in zip(holders, funders):
            if isinstance(f, str):
                groups[f] += float(h.get("uiAmount") or 0)
        worst_funder, worst_amt = max(groups.items(), key=lambda kv: kv[1], default=(None, 0.0))
        pct = 100 * worst_amt / PUMP_SUPPLY
        dev_linked = worst_funder == s.dev
        verdict = "veto" if pct > self.th.max_cluster_pct or (dev_linked and pct > 5) else "ok"
        return [Spike(self.name, "bubblemaps.cluster", verdict, f"{pct:.1f}% linked" + (" · dev-funded" if dev_linked else ""), min(1, pct / 50))]
