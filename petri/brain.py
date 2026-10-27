"""The dish. Stimuli come in, every region fires, the prefrontal decides, the motor acts."""
from __future__ import annotations

import asyncio
import time

import httpx
from rich.console import Console

from .bus import Bus, Spike, Stimulus
from .config import Config
from .feeds.pumpportal import PumpPortal
from .feeds.solana_rpc import RPC
from .regions import Amygdala, Auditory, Cerebellum, Dopamine, Hippocampus, Motor, Prefrontal, Visual
from .regions.cerebellum import Position

con = Console()
OBSERVE_S = 6.0  # let the launch play out before judging (bundles/snipers land in the first seconds)

ICON = {"ok": "[green]✓[/]", "warn": "[yellow]~[/]", "veto": "[bold red]✕[/]"}


def last_price(trades: list[dict]) -> float | None:
    for t in reversed(trades):
        sol, tok = float(t.get("solAmount") or 0), float(t.get("tokenAmount") or 0)
        if sol and tok:
            return sol / tok
    return None


class Brain:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.bus = Bus()
        self.http = httpx.AsyncClient(headers={"user-agent": "petri/0.1"})
        self.rpc = RPC(cfg.rpc_url, self.http)
        self.feed = PumpPortal()
        th = cfg.thresholds
        self.amygdala = Amygdala(self.rpc, th)
        self.hippocampus = Hippocampus(cfg.db_path)
        self.visual = Visual(self.rpc, self.http, th)
        self.auditory = Auditory(self.http, cfg.x_bearer, th)
        self.prefrontal = Prefrontal(cfg.exits.size_sol)
        self.dopamine = Dopamine()
        self.cerebellum = Cerebellum(cfg.exits)
        self.motor = Motor(self.http, self.rpc, cfg.live, cfg.private_key_b58)
        self.positions: dict[str, Position] = {}

    async def think(self, s: Stimulus) -> None:
        await asyncio.sleep(OBSERVE_S)
        trades = self.feed.trades.get(s.mint, [])
        spikes: list[Spike] = [self.hippocampus.check(s)]
        if spikes[0].verdict != "veto":  # known rugger → instant zap, don't waste RPC
            spikes += self.amygdala.launch_buys(s, trades)
            spikes.append(self.visual.curve(s, trades))
            results = await asyncio.gather(
                self.amygdala.authorities(s), self.amygdala.clusters(s), self.visual.top10(s), self.auditory.check(s),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    spikes.append(Spike("SYSTEM", "rpc", "warn", type(r).__name__))
                else:
                    spikes += r if isinstance(r, list) else [r]
        for sp in spikes:
            self.bus.fire(sp)
        d = self.prefrontal.decide(spikes)
        con.print(f"\n[bold]{s.symbol}[/] [dim]{s.mint[:6]}…{s.mint[-4:]}[/]")
        for sp in spikes:
            con.print(f"  {ICON[sp.verdict]} [cyan]{sp.region:<11}[/] {sp.check:<20} {sp.detail}")
        if d.action == "ZAP":
            self.dopamine.pain()
            self.hippocampus.remember(s.dev, d.reason[:80], s.symbol)
            con.print(f"  [bold yellow]ZAP ⚡[/] [red]{d.reason}[/]  [dim](dev memorised)[/]")
            await self.feed.forget(s.mint)
        elif d.action == "BUY":
            res = await self.motor.trade("buy", s.mint, d.size_sol, True)
            price = last_price(self.feed.trades.get(s.mint, [])) or 0
            self.positions[s.mint] = Position(s.mint, s.symbol, price, d.size_sol)
            con.print(f"  [bold green]SPIKE → BUY[/] {d.size_sol} SOL {'(paper)' if res.get('paper') else res.get('sig')}")
        else:
            con.print(f"  [dim]skip: {d.reason}[/]")
            await self.feed.forget(s.mint)

    async def manage(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            for mint, pos in list(self.positions.items()):
                price = last_price(self.feed.trades.get(mint, []))
                if not price or not pos.entry_price:
                    continue
                for reason, frac in self.cerebellum.step(pos, price):
                    await self.motor.trade("sell", mint, f"{int(frac * 100)}%", False)
                    pnl = pos.size_sol * frac * (price / pos.entry_price - 1)
                    pos.remaining -= frac
                    self.dopamine.reward(pnl, [])
                    con.print(f"[green]SELL {pos.symbol} {reason}[/] {frac:.0%} → {pnl:+.3f} SOL  [dim]session {self.dopamine.realized_sol:+.3f}[/]")
                if pos.remaining <= 1e-6:
                    del self.positions[mint]
                    await self.feed.forget(mint)

    async def run(self) -> None:
        mode = "[bold red]LIVE[/]" if self.cfg.live else "[bold cyan]PAPER[/]"
        con.print(f"[bold magenta]PETRI[/] online · {mode} · memory: {self.hippocampus.count()} ruggers")
        asyncio.create_task(self.manage())
        async for s in self.feed.stream():
            asyncio.create_task(self.think(s))
