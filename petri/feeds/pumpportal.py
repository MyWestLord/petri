"""pump.fun new-mint + trade stream via PumpPortal's public websocket."""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator

import websockets

from ..bus import Stimulus

WS_URL = "wss://pumpportal.fun/api/data"


class PumpPortal:
    def __init__(self) -> None:
        self.ws = None
        self.trades: dict[str, list[dict]] = {}

    async def stream(self) -> AsyncIterator[Stimulus]:
        backoff = 1
        while True:
            try:
                async with websockets.connect(WS_URL, ping_interval=20) as ws:
                    self.ws = ws
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    backoff = 1
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("txType") == "create":
                            mint = msg["mint"]
                            self.trades[mint] = []
                            await ws.send(json.dumps({"method": "subscribeTokenTrade", "keys": [mint]}))
                            yield Stimulus(
                                mint=mint,
                                symbol="$" + str(msg.get("symbol", "?")).upper(),
                                name=msg.get("name", ""),
                                dev=msg.get("traderPublicKey", ""),
                                source="pump",
                                created_at=time.time(),
                                market_cap_sol=float(msg.get("marketCapSol", 0) or 0),
                                meta={"initial_buy": msg.get("initialBuy"), "v_sol": msg.get("vSolInBondingCurve")},
                            )
                        elif msg.get("txType") in ("buy", "sell") and msg.get("mint") in self.trades:
                            msg["_t"] = time.time()
                            self.trades[msg["mint"]].append(msg)
            except Exception as e:  # reconnect forever
                print(f"[pumpportal] {e!r}, reconnecting in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def forget(self, mint: str) -> None:
        self.trades.pop(mint, None)
        if self.ws:
            await self.ws.send(json.dumps({"method": "unsubscribeTokenTrade", "keys": [mint]}))
