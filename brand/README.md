# BMTNews brand source — v3 / 2026-10-01

Approved direction: Rare Messenger / 稀有信使. Detached round head, rounded body,
one negative-space news slot and off-center yellow observation ring, without
a letter b shape. The sole authoritative specification is [logo-spec.md](logo-spec.md);
its public media-kit copy is generated, never edited independently.

- `mark.svg`: canonical 512 × 512 body / eye / pupil paths, not raster tracing.
- `wordmark-path.svg`: existing outlined wordmark, no runtime font dependency.
- `LICENSE_LIBERATION.txt`: retained Liberation Sans source typeface notice.
- Public SVG, PNG, platform icons and ZIP are generated under `docs/`.

## Rebuild

```sh
python3 scripts/build_brand_assets.py
node scripts/render_brand_assets.mjs /absolute/path/to/installed/sharp
python3 scripts/build_brand_assets.py --package
```

Python steps use the standard library; sharp is an optional design tool, not a
new application dependency. `--font` is only for approved wordmark changes with
fontTools. Website and Canvas reuse all three master paths. Do not hand-edit
generated SVGs. v1/v2 versioned icons and ZIPs remain byte-identical; v3 uses new
URLs. Application version and PWA identity are unchanged. CSS/JS fingerprints
only need updating in both configs when those asset contents change.
