"""Validate captured MacAgentBench receipts against current native readiness."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.cu.macos_qualification import evaluate_macos_qualification
from jarvis.cu.macos_readiness import probe_macos_readiness


def _print(payload: dict[str, Any], *, pretty: bool) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


async def _run(receipts_path: Path, *, pretty: bool) -> int:
    try:
        receipts_text = await asyncio.to_thread(receipts_path.read_text, encoding="utf-8")
        receipts = json.loads(receipts_text)
    except (OSError, json.JSONDecodeError) as exc:
        _print({"error": f"could not read receipt JSON: {exc}"}, pretty=pretty)
        return 2
    if not isinstance(receipts, dict):
        _print({"error": "receipt JSON must be an object keyed by scenario ID"}, pretty=pretty)
        return 2

    readiness = await probe_macos_readiness()
    qualification = evaluate_macos_qualification(readiness, receipts)
    _print(qualification.to_dict(), pretty=pretty)
    return 0 if qualification.native_qualification_complete else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", type=Path, help="JSON object keyed by scenario ID")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON output")
    args = parser.parse_args()
    return asyncio.run(_run(args.receipts, pretty=args.pretty))


if __name__ == "__main__":
    raise SystemExit(main())
