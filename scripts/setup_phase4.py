"""One-shot Phase 4 setup: export CSVs, generate PBIP, validate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent


def run(name: str) -> None:
    print(f"\n>>> {name}")
    r = subprocess.run([sys.executable, str(SCRIPTS / name)], cwd=str(ROOT))
    if r.returncode != 0:
        sys.exit(r.returncode)


def main() -> None:
    print("Phase 4 setup")
    run("export_powerbi_data.py")
    run("generate_powerbi_pbip.py")
    run("validate_powerbi_export.py")
    print("\nDone. Open powerbi/Olist_Ecommerce_Dashboard.pbip in Power BI Desktop.")
    print("See docs/PHASE4_POWERBI.md for visuals + Save As .pbix")


if __name__ == "__main__":
    main()
