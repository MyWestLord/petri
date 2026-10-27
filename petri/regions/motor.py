"""MOTOR — execution. Paper trading by default. Live mode signs PumpPortal local txs with YOUR burner key."""
from __future__ import annotations

import base64
import time

import httpx

from ..feeds.solana_rpc import RPC


class Motor:
    name = "MOTOR"

    def __init__(self, http: httpx.AsyncClient, rpc: RPC, live: bool, private_key_b58: str | None) -> None:
        self.http, self.rpc, self.live = http, rpc, live
        self.kp = None
        if live:
            from solders.keypair import Keypair  # only needed for live mode
            self.kp = Keypair.from_base58_string(private_key_b58)

    async def trade(self, side: str, mint: str, amount: float, denominated_in_sol: bool, slippage: int = 15) -> dict:
        t0 = time.perf_counter()
        if not self.live:
            return {"paper": True, "side": side, "mint": mint, "amount": amount, "latency_ms": 0}
        from solders.transaction import VersionedTransaction

        r = await self.http.post("https://pumpportal.fun/api/trade-local", data={
            "publicKey": str(self.kp.pubkey()), "action": side, "mint": mint, "amount": amount,
            "denominatedInSol": "true" if denominated_in_sol else "false", "slippage": slippage,
            "priorityFee": 0.0005, "pool": "auto",
        }, timeout=10)
        r.raise_for_status()
        tx = VersionedTransaction(VersionedTransaction.from_bytes(r.content).message, [self.kp])
        sig = await self.rpc.call("sendTransaction", [base64.b64encode(bytes(tx)).decode(), {"encoding": "base64", "skipPreflight": True}])
        return {"paper": False, "sig": sig, "latency_ms": int((time.perf_counter() - t0) * 1000)}
