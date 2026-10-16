"""One place to switch TabPFN model versions.

"v3.5": TabPFN-3.5, Prior Labs' latest (non-commercial weights). Used for the demo.
"v2":   TabPFN-2, Apache 2.0 weights with attribution, so a PAID version of
        Stall Sense could legally ship on it.

Override for a single run:  STALLSENSE_TABPFN=v2 uv run python -m forecast.backtest
"""

import os

MODEL_VERSION = os.environ.get("STALLSENSE_TABPFN", "v3.5")
