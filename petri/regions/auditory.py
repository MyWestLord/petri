"""AUDITORY — listens to X. Separates organic KOL mentions from paid shills."""
from __future__ import annotations

import re

import httpx

from ..bus import Spike, Stimulus
from ..config import Thresholds

PAID_HINTS = re.compile(r"\b(ad|paid|promo|sponsored|partner|#ad)\b|100x|1000x|🚀{3,}", re.I)


class Auditory:
    name = "AUDITORY"

    def __init__(self, http: httpx.AsyncClient, bearer: str | None, th: Thresholds, kol_list: set[str] | None = None) -> None:
        self.http, self.bearer, self.th = http, bearer, th
        self.kols = {k.lower() for k in (kol_list or set())}

    async def check(self, s: Stimulus) -> Spike:
        if not self.bearer:
            return Spike(self.name, "kol.mentions", "ok", "X disabled (no PETRI_X_BEARER)", 0.0)
        r = await self.http.get(
            "https://api.x.com/2/tweets/search/recent",
            params={"query": f"({s.mint} OR \"{s.symbol}\") -is:retweet", "max_results": 50, "expansions": "author_id", "user.fields": "username"},
            headers={"Authorization": f"Bearer {self.bearer}"}, timeout=10,
        )
        if r.status_code != 200:
            return Spike(self.name, "kol.mentions", "ok", f"X api {r.status_code}", 0.0)
        data = r.json()
        users = {u["id"]: u["username"].lower() for u in data.get("includes", {}).get("users", [])}
        organic = paid = 0
        for tw in data.get("data", []):
            if PAID_HINTS.search(tw["text"]):
                paid += 1
            elif not self.kols or users.get(tw["author_id"]) in self.kols:
                organic += 1
        verdict = "veto" if paid > organic else ("ok" if organic >= self.th.min_organic_kols else "warn")
        return Spike(self.name, "kol.mentions", verdict, f"{organic} organic · {paid} paid", min(1, organic / 10))
