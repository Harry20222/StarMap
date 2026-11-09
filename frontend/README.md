# GOODS-S field explorer

The React app loads its map metadata and 43 quality-A galaxy records from the
MongoDB-backed Python API. Inspect a galaxy or compare a pair using the real
JADES GOODS-S image. JSON exports are retained only for migration and regression.

## Run

Start `python app.py` from the repository root with both `MONGODB_URI` and
`MONGODB_DATABASE` configured on Python. Import the source catalog first with
`python migrate_mongodb.py`; see the root README for the complete environment setup.
Then run these commands in `frontend`:

```powershell
npm ci
npm run dev
npm run build
npm run preview
```

Vite development and preview proxy `/api` to `http://127.0.0.1:8000`; Python must
be running. Override the local target with `STARMAP_API_PROXY` if needed.
Production uses Vercel's existing `/api` rewrite to its Python service.
No MongoDB settings belong in browser code or `VITE_*` variables.

## Data flow

- `src/data/api.ts`: map listing, metadata/catalog requests, and on-demand
  comparisons; bounded fetches, cancellation, and friendly errors.
- `src/data/galaxies.ts`: typed records, metadata validation, joins by full ID,
  quality-A/in-image selection, and the original pixel-center transform.
- `src/data/useComparison.ts`: async comparison state, retry, abort and stale
  response protection. No pair table or cosmology calculation in JavaScript.
- `src/FieldLoader.tsx`: loading, empty, API/database error states and Retry.
- `src/App.tsx`: Inspect/Compare selections and reset behavior.
- `GalaxyMap`, `GalaxySearch`, `GalaxyPopup`, `ComparisonPanel`: the existing
  display/interaction components. `markerLayout.ts` retains overlap priority.
- `MapImage.tsx`: resolves MongoDB asset references to Vite's hashed static WebPs
  and requests one appropriately sized variant. Grayscale waits for its toggle.

The inspector receives Python-calculated `distance_from_us` (`ly`, `comoving`).
Comparison results preserve A/B order, degrees, light-years, Planck18, and nulls
for unavailable measurements. A failed comparison retains both selected rings
and provides Retry comparison. Older responses cannot replace a newer pair.
The current static image manifest supports GOODS-S; additional map assets can
be added there with their MongoDB metadata without changing the fetching layer.

## Alignment and interaction

Backend markers describe zero-based pixel **centers** with a bottom-left origin.
The static color PNG is flipped for top-left display. The data adapter computes exactly
`y_display = height - 1 - y`; X stays unchanged. SVG image edges and the viewBox
begin at `-0.5`, so integer marker coordinates represent pixel centers without a
half-pixel shift. The image and overlay resize as one coordinate system.

Rings have no fill and a thin visible stroke. A ResizeObserver recomputes their
visibility whenever the actual image width changes. Priority is quality first,
then larger **F200W_RHALF** (published DR2 circularized half-light radius in
arcseconds), then full ID for ties or incomparable sizes. The comparison includes
the largest possible selected outline plus a small gap. The greedy result is a
maximal set respecting priority, not a claim of globally maximizing marker count.
Hidden markers are omitted from the SVG but remain selectable through search.
Selections are pinned before other markers are laid out, so their circles stay
visible through resizing. Other markers that collide with a selection are hidden.
Two selected circles may overlap when their galaxies are close; neither position
is shifted. Both full IDs remain in the comparison panel. The legend shows the
current visible/total and hidden counts, which can change with selection.

Invisible hit circles provide
44-pixel touch areas where possible. Dense regions can have overlapping hit
areas: a pointer event selects the nearest actual galaxy center rather than
relying on paint order. Keyboard users can Tab to each ring and press Enter or
Space. In **Inspect**, one galaxy opens its existing popup. In **Compare**, drag
from one visible ring to another, or select A and B in sequence with click/tap/
keyboard. Search can supply either or both galaxies, including normally hidden
ones. **Try an example pair** selects `goods-s-deephst:21598` and
`goods-s-deephst:21842` and requests their measurements from the Python API. No
measurements are hard-coded. Empty-sky releases, a drag
back to the starting galaxy, or selecting A twice cancel the unfinished pair.
Escape and Clear comparison reset it. Clicking the already active Inspect or
Compare mode does nothing; switching between different modes still clears the
selection. Resizing keeps selections pinned. Amber rings and a line identify
the comparison. The line is angular separation on the sky, while the calculated
3D separation also uses both radial comoving distances. On phones the completed
result follows the map and scrolls into view; choosing A alone does not scroll
the user away from the map.

Information buttons follow scientific terms as small raised circled icons.
They show plain-language definitions on hover, focus, or tap; outside clicks and
Escape dismiss them. The tooltip is placed within the viewport. Escape closes
an open definition before it clears the galaxy selection or comparison.

The color asset is generated once, not at runtime. To regenerate it from the
repository root, run `python -m starmap.color_image` with the project environment.
The first run retrieves matching WCS-based F090W/F444W crops from MAST; later runs
reuse `data/cache/color/`. The existing F200W cutout is the alignment reference.
Background subtraction, channel balance, and a shared-intensity Lupton asinh
stretch reveal faint sources while compressing bright cores. These display
adjustments do not change any catalog, marker, or distance. Source URLs, hashes,
registration checks, and exact rendering settings are in `results/goods_s_color.md`.

To regenerate the display variants from those unchanged PNGs, run
`python frontend/scripts/export_map_images.py` from the repository root with
the existing environment (Pillow is already available). This exports the entire
square image at 640, 1280, and 2000 pixels using Lanczos resizing and WebP quality
90, with no recrop, rotation, or new color stretch. Files live in `src/assets/`.
The SVG keeps its original 2000-unit coordinate grid regardless of asset size.
`MapImage` waits for the measured image width, considers device pixel ratio, and
sets only one image URL. Color is the default; grayscale image bytes are fetched
only when that mode is chosen. The original scientific PNGs remain unchanged.

The 640/1280 color variants are 87,678 / 463,934 bytes; grayscale variants are
91,598 / 469,752 bytes. Vite emits content-hashed filenames. The root Vercel
headers apply one-year immutable caching only to hashed `/assets/` filenames;
stable names and the homepage do not match that rule. `frame-ancestors 'none'`
is the explicit embedding policy because the portfolio links to StarMap.

## Verification

```powershell
npx playwright install chromium
npm test
npm run build
```

Playwright starts the real Python WSGI application against a fresh in-memory
mongomock database on 8001 and Vite on 5173, with no live MongoDB credential use.
Install `.[dev]` into the Python interpreter; use `STARMAP_TEST_PYTHON` to override
its auto-detection. Both test ports must be free.

Desktop/mobile checks cover visible/hidden galaxy search, inspector metadata,
click/tap/drag/keyboard comparison, reverse order, example pair, cancellation,
resize/collision handling, color/grayscale variants, all marker centers at
320–1440 widths, scientific tooltips, loading/empty/errors/retry and delayed
responses. The original 15-galaxy/105-pair page and synchronous export adapter
live only under `tests/fixtures`; they are not part of the production bundle.
Python tests independently verify all 903 API comparisons and database behavior.
