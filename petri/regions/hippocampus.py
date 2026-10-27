"""HIPPOCAMPUS — memory. Every rugger dev and every funder behind them, forever (sqlite)."""
from __future__ import annotations

import sqlite3
import time

from ..bus import Spike, Stimulus


class Hippocampus:
    name = "HIPPOCAMPUS"

    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("create table if not exists ruggers(wallet text primary key, reason text, coin text, ts real)")
        self.db.commit()

    def remember(self, wallet: str, reason: str, coin: str) -> None:
        self.db.execute("insert or replace into ruggers values(?,?,?,?)", (wallet, reason, coin, time.time()))
        self.db.commit()

    def recall(self, wallet: str) -> tuple[str, str] | None:
        row = self.db.execute("select reason, coin from ruggers where wallet=?", (wallet,)).fetchone()
        return tuple(row) if row else None

    def count(self) -> int:
        return self.db.execute("select count(*) from ruggers").fetchone()[0]

    def check(self, s: Stimulus) -> Spike:
        hit = self.recall(s.dev)
        if hit:
            return Spike(self.name, "dev.wallet", "veto", f"MATCH: rugged {hit[1]} ({hit[0]})", 1.0)
        return Spike(self.name, "dev.wallet", "ok", "clean · never seen", 0.2)
