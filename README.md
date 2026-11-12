# 2005.phonofestivalen.no
Recreation of the 2005 version of phonofestivalen.no (Studentradioen i Bergen), cleaned for local/static hosting.

HTML files use short names matching the original site paths (e.g. `index.html`, `styre.html`, `pressemelding.html`).

Refresh links after edits:

```bash
python3 scripts/update-all-links.py
```

(`scripts/sync-links-from-archive.py` re-fetches body markup from the Internet Archive when network access works.)
