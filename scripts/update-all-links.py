#!/usr/bin/env python3
"""Refresh every in-site href/src: run localize-links plus offline nav/index fixes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "localize_links", ROOT / "scripts" / "localize-links.py"
)
assert _spec and _spec.loader
ll = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ll)

MAIN = ll.MAIN
INDEX = ROOT / MAIN

INDEX_HEADLINES: dict[str, str] = {
    "a000105": "pressemelding.html",
    "a000103": "pressemelding.html",
    "a000102": "presseinvitasjo.html",
}

PAGER_FIXES: dict[str, tuple[str | None, str | None]] = {
    "com_brasa.html": ("pressemelding.html", "bjarn_torske_1.html"),
    "bilder_fra_dine_1.html": ("et_mate_mellom.html", "index.html"),
}

CANONICAL_MAP = """<map name="Map">
 <area shape="rect" coords="433,216,481,238" href="index.html">
  <area shape="rect" coords="366,216,421,238" href="partnere.html">
  <area shape="rect" coords="310,216,353,238" href="index.html" target="_blank">
  <area shape="rect" coords="266,216,298,238" href="index.html">
  <area shape="rect" coords="199,216,254,238" href="index.html">
  <area shape="rect" coords="133,216,186,238" href="index.html">
  <area shape="rect" coords="69,216,122,238" href="index.html">
  <area shape="rect" coords="9,216,59,238" href="index.html">
 <area shape="rect" coords="564,69,719,170" href="index.html" target="_blank">
 <area shape="poly" coords="728,11,689,16,692,36,731,30" href="index.html" target="_blank">
</map>"""

MAP_RE = re.compile(r"<map name=\"Map\">[\s\S]*?</map>", re.I)
PAGER_RE = re.compile(
    r"(<p align=\"right\">)([\s\S]*?)(</p>)",
    re.I,
)


def link_index_headlines(html: str) -> str:
    for elem_id, target in INDEX_HEADLINES.items():
        if target not in ll.LOCAL_FILES:
            continue
        pat = rf'(<h3 id="{re.escape(elem_id)}">)([^<]+)(</h3>)'
        html = re.sub(
            pat,
            rf'\1<a href="{target}">\2</a>\3',
            html,
            count=1,
        )
    return html


def fix_pager(fname: str, html: str) -> str:
    if fname not in PAGER_FIXES:
        return html
    prev_href, next_href = PAGER_FIXES[fname]
    block = (
        f'<p align="right">\n'
        f'<a href="{prev_href}">&laquo; Forrige</a> |\n\n'
        f'<a href="#" onclick="history.go(-1);return false;">Gå tilbake</a>\n'
        f'| <a href="{next_href}">Neste &raquo;</a>\n\n</p>'
    )
    return PAGER_RE.sub(block, html, count=1)


def restore_back_links(html: str) -> str:
    return re.sub(
        r"\|\s*Gå tilbake\s*\|",
        r'| <a href="#" onclick="history.go(-1);return false;">Gå tilbake</a> |',
        html,
    )


def apply_canonical_map(html: str) -> str:
    if '<map name="Map">' not in html:
        return html
    return MAP_RE.sub(CANONICAL_MAP, html, count=1)


def main() -> int:
    ll.refresh_local_files()
    changed = 0
    for path in sorted(ROOT.glob("*.html")):
        before = path.read_text(encoding="utf-8", errors="replace")
        html = ll.strip_nonlocal_head_links(before)
        html = ll.localize_attrs(html)
        html = ll.unwrap_external_anchors(html)
        html = re.sub(r'<a\s+href=(["\'])#\1\s*></a>', "", html, flags=re.I)
        html = apply_canonical_map(html)
        html = restore_back_links(html)
        if path.name != MAIN:
            html = fix_pager(path.name, html)
        if path.name == MAIN:
            html = link_index_headlines(html)
        if html != before:
            path.write_text(html, encoding="utf-8")
            changed += 1

    ll.refresh_local_files()
    problems = ll.verify()
    print(f"updated {changed} html files")
    if problems:
        print("remaining issues:", len(problems))
        for p in problems[:25]:
            print(" ", p)
        return 1
    print("all href/src are local")
    return 0


if __name__ == "__main__":
    sys.exit(main())
