# 2005.phonofestivalen.no
Recreation of the 2005 version of phonofestivalen.no (Studentradioen i Bergen), cleaned for local/static hosting.

## Layout

- `index.html` and top-level pages at the repo root
- Archive posts in `articles/`
- Styles in `css/styles-site.css`
- Images in `images/`
- Feeds: `atom.xml`, `index.xml`, `index.rdf`

## GitHub Pages

1. Push this repository to GitHub.
2. **Settings → Pages → Build and deployment**: choose **Deploy from a branch**, branch **main**, folder **/ (root)**.
3. Open `https://<user>.github.io/<repo>/` (project site) or your custom domain.

Relative links work from any Pages URL. `.nojekyll` is included so paths are served as-is.

After adding raw Internet Archive HTML:

```bash
python3 scripts/strip-wayback.py
python3 scripts/fix-site-links.py
```

(`scripts/sync-links-from-archive.py` re-fetches body markup from the Internet Archive when network access works.)
