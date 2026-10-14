"""Print the side-effect-free MacAgentBench readiness and scenario matrix as JSON.

This command never clicks, types, opens a TCC prompt or claims that native
qualification passed. Run it on the physical Mac before collecting live
receipts::

    python scripts/macos_agent_bench_preflight.py --pretty
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.cu.macos_qualification import build_macos_qualification_preflight
from jarvis.cu.macos_readiness import probe_macos_readiness


async def _run(*, pretty: bool) -> int:
    report = await probe_macos_readiness()
    bundle = build_macos_qualification_preflight(report)
    print(json.dumps(bundle.to_dict(), indent=2 if pretty else None, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pretty", action="store_true", help="indent the JSON output")
    args = parser.parse_args()
    return asyncio.run(_run(pretty=args.pretty))


if __name__ == "__main__":
    raise SystemExit(main())
