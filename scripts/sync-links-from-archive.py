#!/usr/bin/env python3
"""Sync in-page links from Internet Archive captures using exact path → local file mapping."""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MAIN = "index.html"

# (local filename, site path, wayback timestamp)
PAGES: list[tuple[str, str, str]] = [
    (MAIN, "/info.html", "20060215154059"),
    ("styre.html", "/arkiv/2005/09/styre.html", "20060215154106"),
    ("frivillige_sake.html", "/arkiv/2005/09/frivillige_sake.html", "20060208061616"),
    ("janemil_kolsta.html", "/arkiv/2005/09/janemil_kolsta.html", "20060215154148"),
    ("karen_jo_fields.html", "/arkiv/2005/09/karen_jo_fields.html", "20060215154231"),
    ("programmet_har.html", "/arkiv/2005/09/programmet_har.html", "20060215154154"),
    ("elvira_nikolais.html", "/arkiv/2005/09/elvira_nikolais.html", "20060208061600"),
    ("filmer_som_sett.html", "/arkiv/2005/09/filmer_som_sett.html", "20060215154215"),
    ("partnere.html", "/arkiv/2005/08/partnere.html", "20060215154118"),
    ("doug_hoekstraus_1.html", "/arkiv/2005/09/doug_hoekstraus_1.html", "20060208061854"),
    ("sgt_petter.html", "/arkiv/2005/08/sgt_petter.html", "20060215154134"),
    ("phonofestivalen.html", "/arkiv/2005/08/phonofestivalen.html", "20060208061628"),
    ("karl_barx.html", "/arkiv/2005/08/karl_barx.html", "20060215154130"),
    ("metall_pa_hulen.html", "/arkiv/2005/08/metall_pa_hulen.html", "20060208061752"),
    ("stereo_total_pa.html", "/arkiv/2005/09/stereo_total_pa.html", "20060208061815"),
    ("x_makeena_pa_sp_1.html", "/arkiv/2005/09/x_makeena_pa_sp_1.html", "20060208061908"),
    ("debattene_pa_ph.html", "/arkiv/2005/09/debattene_pa_ph.html", "20060208061758"),
    ("teaterstykket_a.html", "/arkiv/2005/09/teaterstykket_a.html", "20060208061838"),
    ("presseinvitasjo.html", "/arkiv/2005/09/presseinvitasjo.html", "20060215154053"),
    ("pressemelding.html", "/arkiv/2005/09/pressemelding.html", "20060215154143"),
    ("bilder_fra_dine_1.html", "/arkiv/2005/10/bilder_fra_dine_1.html", "20060208061625"),
    ("sydlandsk_stemn.html", "/arkiv/2005/09/sydlandsk_stemn.html", "20060208061834"),
    ("fnforedrag_avly.html", "/arkiv/2005/09/fnforedrag_avly.html", "20060215154223"),
    ("stinn_brakke_pa.html", "/arkiv/2005/09/stinn_brakke_pa.html", "20060208061823"),
    ("programmet_for.html", "/arkiv/2005/09/programmet_for.html", "20060208061740"),
    ("doug_hoekstra_a.html", "/arkiv/2005/09/doug_hoekstra_a.html", "20060208061809"),
    ("et_mate_mellom.html", "/arkiv/2005/10/et_mate_mellom.html", "20060208061746"),
    ("william_hut.html", "/arkiv/2005/09/william_hut.html", "20060208061725"),
    ("the_catastrophe.html", "/arkiv/2005/09/the_catastrophe.html", "20060208061847"),
    ("x_makeena_fr.html", "/arkiv/2005/09/x_makeena_fr.html", "20060208061634"),
    ("bjarn_torske_1.html", "/arkiv/2005/09/bjarn_torske_1.html", "20060208061730"),
    ("com_brasa.html", "/arkiv/2005/09/com_brasa.html", "20060208061709"),
    ("odd_martin_skal.html", "/arkiv/2005/09/odd_martin_skal.html", "20060215154237"),
    ("karen_jo_fields_1.html", "/arkiv/2005/09/karen_jo_fields_1.html", "20060215154307"),
    ("doug_hoekstraus.html", "/arkiv/2005/09/doug_hoekstraus.html", "20060215154208"),
]

PATH_TO_FILE: dict[str, str] = {path: fname for fname, path, _ in PAGES}
PATH_TO_FILE["/index.html"] = MAIN
PATH_TO_FILE["/partnere.html"] = PATH_TO_FILE["/arkiv/2005/08/partnere.html"]
PATH_TO_FILE["/arkiv/2005/09/pressemelding_2.html"] = "pressemelding.html"

LOCAL_FILES: set[str] = set()
ARCHIVE_PREFIX = re.compile(r"https?://web\.archive\.org/web/\d+(?:[a-z]{2}_)?/", re.I)
REL_WEB_PREFIX = re.compile(r"/web/\d+(?:[a-z]{2}_)?/(?:https?://)?", re.I)
HEAD_RE = re.compile(
    r"<head>\s*(?:(?!<!-- End Wayback Rewrite JS Include -->).)*"
    r"<!-- End Wayback Rewrite JS Include -->\s*",
    re.DOTALL | re.IGNORECASE,
)
TOOLBAR_RE = re.compile(
    r"<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->\s*",
    re.DOTALL | re.IGNORECASE,
)
FOOTER_RE = re.compile(r"</html>\s*<!--\s*FILE ARCHIVED[\s\S]*$", re.I)
CONTAINER_INNER = re.compile(
    r'<div id="container">[\s\S]*?<div style="clear: both;">&#160;</div>',
    re.DOTALL,
)
CONTAINER_IN_CURRENT = CONTAINER_INNER
ATTR_RE = re.compile(r'\b(href|src)=(["\'])([^"\']*)\2', re.I)
A_TAG_RE = re.compile(r"<a\b[^>]*href=(['\"])([^'\"]+)\1[^>]*>(.*?)</a>", re.I | re.DOTALL)


def refresh_local_files() -> None:
    LOCAL_FILES.clear()
    LOCAL_FILES.update(p.name for p in ROOT.iterdir() if p.is_file())


def fetch_archive(path: str, timestamp: str) -> str:
    url = f"https://web.archive.org/web/{timestamp}/http://www.phonofestivalen.no:80{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "phonofestivalen-mirror/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def unwrap_url(url: str) -> str:
    url = ARCHIVE_PREFIX.sub("", url)
    url = REL_WEB_PREFIX.sub("", url)
    return url.strip()


def path_to_local(url: str) -> str | None:
    url = unwrap_url(url)
    if not url or url.startswith("#"):
        return None
    if url.lower() in ("null", "javascript:void(0)"):
        return None
    if url.startswith("mailto:") or url.startswith("javascript:"):
        return None

    parsed = urlparse(url if "://" in url else f"http://{url}" if url.startswith("www.") else url)
    if parsed.scheme in ("http", "https"):
        if "phonofestivalen.no" not in (parsed.netloc or "").lower():
            return None
        path = parsed.path or "/"
        frag = f"#{parsed.fragment}" if parsed.fragment else ""
        if path in PATH_TO_FILE:
            return PATH_TO_FILE[path] + frag
        if path.endswith(".html") or path == "/":
            return MAIN + frag
        return None

    if parsed.scheme == "" and not url.startswith("/"):
        base, _, frag = url.partition("#")
        if base in LOCAL_FILES:
            return url
        return None

    if url.startswith("/"):
        parsed = urlparse(f"http://www.phonofestivalen.no{url}")
        path = parsed.path
        frag = f"#{parsed.fragment}" if parsed.fragment else ""
        if path in PATH_TO_FILE:
            return PATH_TO_FILE[path] + frag
        if path.endswith(".html"):
            return MAIN + frag
    return None


def local_image(url: str) -> str | None:
    url = unwrap_url(url)
    parsed = urlparse(url if "://" in url else f"http://x{url}")
    base = Path(parsed.path).name
    if base.lower() in {n.lower() for n in LOCAL_FILES}:
        for n in LOCAL_FILES:
            if n.lower() == base.lower():
                return n
    return None


def strip_wayback(html: str) -> str:
    html = HEAD_RE.sub("<head>\n", html, count=1)
    html = TOOLBAR_RE.sub("", html)
    html = FOOTER_RE.sub("</html>\n", html)
    html = re.sub(r"<body>\s*", "<body>\n\n", html, count=1)
    return html


def localize_html(html: str) -> str:
    def attr_repl(m: re.Match[str]) -> str:
        attr, quote, val = m.group(1), m.group(2), m.group(3)
        if attr.lower() == "href":
            local = path_to_local(val)
            if local:
                return f'href={quote}{local}{quote}'
            if unwrap_url(val).startswith(("http://", "https://", "www.", "mailto:")) or val.startswith(
                ("javascript:", "mailto:")
            ):
                return f'href={quote}#{quote}'
            return m.group(0)
        local_img = local_image(val)
        if local_img:
            return f'src={quote}{local_img}{quote}'
        if "phonofestivalen.no" in unwrap_url(val) or "/web/" in val or "archive.org" in val:
            return f'src={quote}missing.gif{quote}'
        base = val.split("#")[0]
        if base in LOCAL_FILES:
            return m.group(0)
        if attr.lower() == "src" and base:
            return f'src={quote}missing.gif{quote}'
        return m.group(0)

    html = ATTR_RE.sub(attr_repl, html)

    def a_repl(m: re.Match[str]) -> str:
        href = m.group(2)
        inner = m.group(3)
        if path_to_local(href):
            return m.group(0)
        if href.strip() in ("#", "") or href.startswith("#"):
            if href == "#":
                return inner
        return inner

    return A_TAG_RE.sub(a_repl, html)


def extract_container(html: str) -> str:
    m = CONTAINER_INNER.search(html)
    if not m:
        raise RuntimeError("container block not found")
    return m.group(0).rstrip() + "\n\n</div>"


def sync_file(fname: str, path: str, timestamp: str) -> None:
    archive_html = fetch_archive(path, timestamp)
    archive_html = strip_wayback(archive_html)
    archive_html = localize_html(archive_html)
    new_tail = extract_container(archive_html)
    if not new_tail:
        raise RuntimeError(f"no #container in archive HTML for {fname}")

    current_path = ROOT / fname
    current = current_path.read_text(encoding="utf-8", errors="replace")
    m = CONTAINER_IN_CURRENT.search(current)
    if not m:
        raise RuntimeError(f"no #container in current {fname}")
    updated = current[: m.start()] + new_tail + current[m.end() :]
    current_path.write_text(updated, encoding="utf-8")


def verify() -> list[str]:
    problems: list[str] = []
    for fp in ROOT.glob("*.html"):
        text = fp.read_text(encoding="utf-8", errors="replace")
        for m in ATTR_RE.finditer(text):
            attr, val = m.group(1).lower(), m.group(3).strip()
            if attr == "href":
                if not val or val == "#" or val.startswith("javascript:"):
                    continue
                base = val.split("#")[0]
                if base not in LOCAL_FILES:
                    problems.append(f"{fp.name}: href {val}")
            elif attr == "src":
                base = val.split("#")[0]
                if base not in LOCAL_FILES:
                    problems.append(f"{fp.name}: src {val}")
        if text.count(f'href="{MAIN}"') >= 8:
            pass
    return problems


def main() -> int:
    refresh_local_files()
    for fname, path, ts in PAGES:
        print("sync", fname)
        try:
            sync_file(fname, path, ts)
        except (urllib.error.URLError, RuntimeError) as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            return 1
        time.sleep(0.3)
    problems = verify()
    if problems:
        print("issues:", len(problems))
        for p in problems[:30]:
            print(" ", p)
        return 1
    print("done — links match archived originals (local files only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
