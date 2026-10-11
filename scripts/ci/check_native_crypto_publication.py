"""Fail fast unless the reviewed native-crypto publication is fully available."""

from __future__ import annotations

import html.parser
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import native_crypto_index as index  # noqa: E402

MAX_INDEX_BYTES = 1024 * 1024
PAGES_SETTINGS_URL = "https://github.com/Sgangalossa/PersonalJarvis/settings/pages"


class _Links(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href is not None:
                self.hrefs.add(href)


def check_publication() -> None:
    records = index.native_records()
    index_url = index.wheel_links_url()
    try:
        with urllib.request.urlopen(index_url, timeout=30) as response:  # noqa: S310
            content = response.read(MAX_INDEX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                "reviewed native-crypto index returned HTTP 404; enable GitHub Pages at "
                f"{PAGES_SETTINGS_URL}, select Source: GitHub Actions, then rerun "
                "Native cryptography wheels on jarvis-lab"
            ) from exc
        raise
    if len(content) > MAX_INDEX_BYTES:
        raise ValueError("Native crypto package index exceeds the 1 MiB safety limit")

    links = _Links()
    links.feed(content.decode("utf-8"))
    for record in records:
        expected = f"{record['url']}#sha256={record['sha256']}"
        if expected not in links.hrefs:
            raise ValueError(f"Native crypto package index is missing {record['filename']}")

    with tempfile.TemporaryDirectory(prefix="native-crypto-publication-") as directory:
        destination = Path(directory)
        for record in records:
            index.fetch_native_wheel(record["target"], destination)


def main() -> int:
    try:
        check_publication()
    except Exception as exc:  # noqa: BLE001 - one actionable CI boundary
        print(f"native crypto publication unavailable: {exc}", file=sys.stderr)
        return 1
    print("native crypto publication is complete and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
