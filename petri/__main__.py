import argparse
import asyncio

from .brain import Brain
from .config import Config

BANNER = r"""
   ____  _____ _____ ____  ___
  |  _ \| ____|_   _|  _ \|_ _|   the pump.fun bot
  | |_) |  _|   | | | |_) || |    with a brain 🧠
  |  __/| |___  | | |  _ < | |
  |_|   |_____| |_| |_| \_\___|   touch a rug → get zapped ⚡
"""


def main() -> None:
    ap = argparse.ArgumentParser(prog="petri")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--live", action="store_true", help="real trades (needs PETRI_PRIVATE_KEY). default: paper")
    a = ap.parse_args()
    cfg = Config.load(a.config)
    if a.live:
        cfg.live = True
        if not cfg.private_key_b58:
            raise SystemExit("--live needs PETRI_PRIVATE_KEY (burner wallet only).")
    print(BANNER)
    try:
        asyncio.run(Brain(cfg).run())
    except KeyboardInterrupt:
        print("\nPETRI went to sleep. 💤")


if __name__ == "__main__":
    main()
