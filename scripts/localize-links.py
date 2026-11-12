#!/usr/bin/env python3
"""Rewrite href/src in HTML to reference only files present in the project root."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAIN = "index.html"

PATH_TO_FILE: dict[str, str] = {
    "/info.html": MAIN,
    "/index.html": MAIN,
    "/": MAIN,
    "/arkiv/2005/09/styre.html": "styre.html",
    "/arkiv/2005/09/frivillige_sake.html": "frivillige_sake.html",
    "/arkiv/2005/09/janemil_kolsta.html": "janemil_kolsta.html",
    "/arkiv/2005/09/karen_jo_fields.html": "karen_jo_fields.html",
    "/arkiv/2005/09/programmet_har.html": "programmet_har.html",
    "/arkiv/2005/09/elvira_nikolais.html": "elvira_nikolais.html",
    "/arkiv/2005/09/filmer_som_sett.html": "filmer_som_sett.html",
    "/arkiv/2005/08/partnere.html": "partnere.html",
    "/partnere.html": "partnere.html",
    "/arkiv/2005/09/doug_hoekstraus_1.html": "doug_hoekstraus_1.html",
    "/arkiv/2005/08/sgt_petter.html": "sgt_petter.html",
    "/arkiv/2005/08/phonofestivalen.html": "phonofestivalen.html",
    "/arkiv/2005/08/karl_barx.html": "karl_barx.html",
    "/arkiv/2005/08/metall_pa_hulen.html": "metall_pa_hulen.html",
    "/arkiv/2005/09/stereo_total_pa.html": "stereo_total_pa.html",
    "/arkiv/2005/09/x_makeena_pa_sp_1.html": "x_makeena_pa_sp_1.html",
    "/arkiv/2005/09/debattene_pa_ph.html": "debattene_pa_ph.html",
    "/arkiv/2005/09/teaterstykket_a.html": "teaterstykket_a.html",
    "/arkiv/2005/09/presseinvitasjo.html": "presseinvitasjo.html",
    "/arkiv/2005/09/pressemelding.html": "pressemelding.html",
    "/arkiv/2005/09/pressemelding_2.html": "pressemelding.html",
    "/arkiv/2005/10/bilder_fra_dine_1.html": "bilder_fra_dine_1.html",
    "/arkiv/2005/09/sydlandsk_stemn.html": "sydlandsk_stemn.html",
    "/arkiv/2005/09/fnforedrag_avly.html": "fnforedrag_avly.html",
    "/arkiv/2005/09/stinn_brakke_pa.html": "stinn_brakke_pa.html",
    "/arkiv/2005/09/programmet_for.html": "programmet_for.html",
    "/arkiv/2005/09/doug_hoekstra_a.html": "doug_hoekstra_a.html",
    "/arkiv/2005/10/et_mate_mellom.html": "et_mate_mellom.html",
    "/arkiv/2005/09/william_hut.html": "william_hut.html",
    "/arkiv/2005/09/the_catastrophe.html": "the_catastrophe.html",
    "/arkiv/2005/09/x_makeena_fr.html": "x_makeena_fr.html",
    "/arkiv/2005/09/bjarn_torske_1.html": "bjarn_torske_1.html",
    "/arkiv/2005/09/com_brasa.html": "com_brasa.html",
    "/arkiv/2005/09/odd_martin_skal.html": "odd_martin_skal.html",
    "/arkiv/2005/09/karen_jo_fields_1.html": "karen_jo_fields_1.html",
    "/arkiv/2005/09/doug_hoekstraus.html": "doug_hoekstraus.html",
}

NAV_FALLBACK = {
    "/kontakt.html": MAIN,
    "/debatter.html": MAIN,
    "/bandogartister.html": MAIN,
    "/program.html": MAIN,
    "/mt/mt.cgi": MAIN,
}

LOCAL_FILES: set[str] = set()
ATTR_RE = re.compile(r'\b(href|src)=(["\'])([^"\']*)\2', re.I)
A_TAG_RE = re.compile(r"<a\b[^>]*href=(['\"])([^'\"]+)\1[^>]*>(.*?)</a>", re.I | re.DOTALL)
LINK_RE = re.compile(r'<link\b[^>]*>', re.I)


def refresh_local_files() -> None:
    LOCAL_FILES.clear()
    LOCAL_FILES.update(p.name for p in ROOT.iterdir() if p.is_file())


def resolve_phonofestivalen(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if "phonofestivalen.no" not in (parsed.netloc or "").lower():
        return None
    path = parsed.path or "/"
    frag = f"#{parsed.fragment}" if parsed.fragment else ""
    if path in PATH_TO_FILE:
        return PATH_TO_FILE[path] + frag
    if path in NAV_FALLBACK:
        return NAV_FALLBACK[path] + frag
    return MAIN + frag


def resolve_url(url: str, attr: str) -> str:
    url = url.strip()
    if not url or url.startswith("#"):
        return url
    if url.lower() in ("null", "undefined"):
        return "#"

    if url.startswith("mailto:") or url.startswith("javascript:"):
        return "#"

    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        local = resolve_phonofestivalen(url)
        if local:
            return local
        return "#"

    if parsed.scheme == "" and not url.startswith("/"):
        base, _, frag = url.partition("#")
        if base in LOCAL_FILES:
            return url
        if base.endswith(".html") and base in LOCAL_FILES:
            return url
        # scheme-less external host
        if "." in base and "/" in base and not base.endswith((".html", ".gif", ".jpg", ".css")):
            return "#"
        if base in LOCAL_FILES:
            return base + (f"#{frag}" if frag else "")
        if base.endswith((".html", ".css", ".gif", ".jpg", ".jpeg", ".png")):
            return "missing.gif" if attr == "src" else MAIN
        return "#"

    if url.startswith("/"):
        return resolve_phonofestivalen(f"http://www.phonofestivalen.no{url}") or MAIN

    return url


def unwrap_external_anchors(html: str) -> str:
    """Replace anchors whose href is not a local file with their inner HTML."""

    def repl(m: re.Match[str]) -> str:
        href = m.group(2).strip()
        inner = m.group(3)
        if href.startswith("#") and href != "#":
            return m.group(0)
        resolved = resolve_url(href, "href")
        if resolved == "#":
            return inner
        if resolved in LOCAL_FILES or (resolved.split("#")[0] in LOCAL_FILES):
            return m.group(0)
        return inner

    return A_TAG_RE.sub(repl, html)


def strip_nonlocal_head_links(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        hm = re.search(r'href=(["\'])([^"\']+)\1', tag, re.I)
        if not hm:
            return tag
        href = hm.group(2)
        if href == "styles-site.css":
            return tag
        rel = re.search(r'\brel=(["\'])([^"\']+)\1', tag, re.I)
        if rel and rel.group(2).lower() in ("edituri", "alternate"):
            return ""
        resolved = resolve_url(href, "href")
        if resolved in LOCAL_FILES or resolved.split("#")[0] in LOCAL_FILES:
            if "rel=" in tag.lower():
                return re.sub(r'href=(["\'])([^"\']+)\1', f'href=\\1{resolved}\\1', tag, count=1)
        return ""

    return LINK_RE.sub(repl, html)


def localize_attrs(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        attr, quote, val = m.group(1), m.group(2), m.group(3)
        new = resolve_url(val, attr)
        if attr == "src" and new != "#":
            base = new.split("#")[0]
            if base not in LOCAL_FILES:
                new = "missing.gif"
        return f'{attr}={quote}{new}{quote}'

    return ATTR_RE.sub(repl, html)


def clean_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    html = strip_nonlocal_head_links(original)
    html = localize_attrs(html)
    html = unwrap_external_anchors(html)
    html = re.sub(r'<a\s+href=(["\'])#\1\s*></a>', "", html, flags=re.I)
    html = re.sub(
        r'<a\s+href=(["\'])#\1[^>]*>\s*Gå tilbake\s*</a>',
        r'<a href="#" onclick="history.go(-1);return false;">Gå tilbake</a>',
        html,
        flags=re.I,
    )
    html = re.sub(
        r'(<area\b[^>]*\bhref=(["\']))#\2',
        rf"\1{MAIN}\2",
        html,
        flags=re.I,
    )
    if html != original:
        path.write_text(html, encoding="utf-8")
        return True
    return False


def verify() -> list[str]:
    problems: list[str] = []
    for fp in ROOT.glob("*.html"):
        text = fp.read_text(encoding="utf-8", errors="replace")
        for m in ATTR_RE.finditer(text):
            val = m.group(3).strip()
            attr = m.group(1).lower()
            if not val or val.startswith("#") or val.startswith("javascript:"):
                continue
            if val.startswith("mailto:"):
                problems.append(f"{fp.name}: mailto {val}")
                continue
            parsed = urlparse(val)
            if parsed.scheme in ("http", "https"):
                problems.append(f"{fp.name}: external {attr} {val}")
                continue
            base = val.split("#")[0]
            if attr == "src" and base not in LOCAL_FILES:
                problems.append(f"{fp.name}: missing src {val}")
            if attr == "href" and base not in LOCAL_FILES and not val.startswith("#"):
                problems.append(f"{fp.name}: bad href {val}")
    return problems


def main() -> int:
    refresh_local_files()
    changed = sum(clean_file(p) for p in ROOT.glob("*.html"))
    print(f"updated {changed} html files")
    problems = verify()
    if problems:
        print("remaining issues:", len(problems))
        for p in problems[:20]:
            print(" ", p)
        return 1
    print("all href/src are local")
    return 0


if __name__ == "__main__":
    sys.exit(main())
