import time

from petri.bus import Spike, Stimulus
from petri.config import Exits, Thresholds
from petri.regions.amygdala import Amygdala
from petri.regions.cerebellum import Cerebellum, Position
from petri.regions.hippocampus import Hippocampus
from petri.regions.prefrontal import Prefrontal


def test_one_red_flag_zaps():
    d = Prefrontal(1.5).decide([Spike("A", "x", "ok", ""), Spike("B", "jito.bundle", "veto", "6 wallets")])
    assert d.action == "ZAP"


def test_all_green_buys():
    d = Prefrontal(1.5).decide([Spike("A", "x", "ok", "") for _ in range(8)])
    assert d.action == "BUY" and d.size_sol == 1.5


def test_hippocampus_never_forgets(tmp_path):
    h = Hippocampus(str(tmp_path / "m.sqlite"))
    h.remember("DEV1", "bundle", "$MOONCAT")
    s = Stimulus("MINT", "$MOONCAT2", "", "DEV1", "pump", time.time())
    assert h.check(s).verdict == "veto"


def test_bundle_detection():
    s = Stimulus("MINT", "$X", "", "DEV", "pump", 1000.0)
    trades = [{"txType": "buy", "traderPublicKey": f"W{i}", "tokenAmount": 50_000_000, "_t": 1000.5} for i in range(6)]
    spikes = {sp.check: sp for sp in Amygdala(None, Thresholds()).launch_buys(s, trades)}
    assert spikes["jito.bundle"].verdict == "veto"
    assert spikes["snipers.block0"].verdict == "veto"


def test_tp_ladder():
    cb = Cerebellum(Exits())
    p = Position("M", "$G", 1.0, 1.5)
    assert cb.step(p, 2.05) == [("TP1", 0.4)]
    assert cb.step(p, 4.1) == [("TP2", 0.4)]
