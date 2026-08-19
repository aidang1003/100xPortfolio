#!/usr/bin/env python3
"""One-command data refresh — rebuild every derived artifact, in order.

    python scripts/refresh.py            # incremental: pick up new index members
    python scripts/refresh.py --refresh  # also re-download the source CSVs

The pipeline is cache-first and immutable: closed eras never change, so this only
does real work for new index members (new price series + fundamentals) and a
fresh membership snapshot. Everything it writes is deterministic — review the
`git diff` and commit the regenerated `app/*.json` + `docs/COVERAGE.md`.

Order (each step feeds the next):
    membership.json -> companies.json -> fundamentals.json -> universe.json -> docs/COVERAGE.md
"""

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_companies  # noqa: E402
import build_fundamentals  # noqa: E402
import build_membership  # noqa: E402
import build_universe  # noqa: E402
import coverage  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Rebuild the 100xPortfolio data artifacts.")
    ap.add_argument("--refresh", action="store_true",
                    help="re-download the source CSVs (index membership + GICS/HQ) before rebuilding")
    args = ap.parse_args()

    if args.refresh:
        cache = os.path.join(HERE, ".cache")
        if os.path.isdir(cache):
            shutil.rmtree(cache)
            print(f"cleared {cache} (source CSVs will be re-downloaded)")

    print("\n[1/5] membership.json — point-in-time index rosters")
    build_membership.build()
    print("\n[2/5] companies.json — names, industries, HQ")
    build_companies.build()
    print("\n[3/5] fundamentals.json — entry price / P·E / yield (incremental)")
    build_fundamentals.main()
    print("\n[4/5] universe.json — assembled game universe (fills any missing price series)")
    build_universe.main()
    print("\n[5/5] docs/COVERAGE.md — coverage report")
    coverage.main()

    print("\n✓ refresh complete. Review `git diff`, then commit the regenerated app/*.json + docs/COVERAGE.md.")


if __name__ == "__main__":
    main()
