"""Minimal Solana JSON-RPC helpers (no SDK needed for reads)."""
from __future__ import annotations

from typing import Any

import httpx


class RPC:
    def __init__(self, url: str, client: httpx.AsyncClient) -> None:
        self.url, self.client, self._id = url, client, 0

    async def call(self, method: str, params: list[Any]) -> Any:
        self._id += 1
        r = await self.client.post(self.url, json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}, timeout=15)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body["result"]

    async def mint_info(self, mint: str) -> dict:
        res = await self.call("getAccountInfo", [mint, {"encoding": "jsonParsed"}])
        return res["value"]["data"]["parsed"]["info"]  # mintAuthority, freezeAuthority, supply, decimals

    async def largest_holders(self, mint: str) -> list[dict]:
        res = await self.call("getTokenLargestAccounts", [mint])
        return res["value"]  # [{address, uiAmount, ...}] token accounts

    async def token_account_owner(self, token_account: str) -> str:
        res = await self.call("getAccountInfo", [token_account, {"encoding": "jsonParsed"}])
        return res["value"]["data"]["parsed"]["info"]["owner"]

    async def first_funder(self, wallet: str) -> str | None:
        """Who sent this wallet its first SOL? Shared funders = bubblemap-style cluster."""
        sigs = await self.call("getSignaturesForAddress", [wallet, {"limit": 1000}])
        if not sigs:
            return None
        oldest = sigs[-1]["signature"]
        tx = await self.call("getTransaction", [oldest, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        if not tx:
            return None
        for ix in tx["transaction"]["message"]["instructions"]:
            p = ix.get("parsed") or {}
            if p.get("type") == "transfer" and p.get("info", {}).get("destination") == wallet:
                return p["info"]["source"]
        return None
