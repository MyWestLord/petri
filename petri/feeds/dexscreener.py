"""DexScreener public API: pairs, volume, price."""
from __future__ import annotations

import httpx

BASE = "https://api.dexscreener.com"


async def token_pairs(client: httpx.AsyncClient, mint: str) -> list[dict]:
    r = await client.get(f"{BASE}/latest/dex/tokens/{mint}", timeout=10)
    r.raise_for_status()
    return r.json().get("pairs") or []


async def best_pair(client: httpx.AsyncClient, mint: str) -> dict | None:
    pairs = await token_pairs(client, mint)
    return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0), default=None)
