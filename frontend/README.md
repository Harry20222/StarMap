# Frontend Prototype 2: GOODS-S field explorer and comparison

Select a ring on the real JADES GOODS-S three-filter color image to inspect one galaxy.
The selectable set is derived from the backend exports, including galaxies
outside the three backend example pairs. There are currently 43 unique quality-A
objects and 903 exported pairs. The visible set is filtered at the current
display width to prevent overlapping circles. **Find a galaxy** searches all 43
IDs, including hidden rings. Select a result with click/tap or Arrow keys and
Enter. The selected galaxy appears at its actual position and opens the inspector.
The map opens in **Color** mode. Use the **Color / Black and white** buttons above
the image to switch between the three-filter composite and the original F200W
grayscale image. Switching updates the image caption and keeps the current galaxy
selection, marker alignment, and popup details unchanged.

## Run

Install Node.js 20.19+ or 22.12+ (tested on Node 24). From this directory:

```powershell
npm ci
npm run dev
```

Open the Local URL printed by Vite. After installing dependencies, you can also
run the repository's `run_frontend.py` with your editor's Run button. That wrapper
launches Vite and opens the browser. It does not calculate distances or host a
Python API. The existing `run_starmap.py` remains the backend launcher.

```powershell
npm run build   # TypeScript check and static output in dist/
npm run preview # Serve the production build locally
```

The production app needs only static HTTP hosting. Its JSON data, image, fonts,
and code are bundled; it has no backend service or external font requests.
Opening index.html using file:// is not supported by browser module security.

## Data flow

1. `src/data/galaxies.ts` imports `../results/markers.json` and
   `../results/measurements.json` from the repository (the imports use the full
   relative path from that module). It joins them by **galaxy_id**, validates
   coordinate conventions and distance units, and filters quality **A** markers
   that lie inside the image. No IDs or sample count are hard-coded.
2. `src/components/GalaxyMap.tsx` displays a static WebP through `MapImage.tsx`
   and interactive rings in one SVG. The variants come directly from the existing
   `results/goods_s_color.png` and `results/goods_s_f200w.png`. Real JADES DR2 F090W, F200W, and F444W SCI
   observations map to blue, green, and red. The color image has exactly the same
   grid as the native 2,000 × 2,000 F200W reference crop, without axes or baked-in
   markers. `results/goods_s_f200w.png` and `results/galaxy_map.png` remain the
   original grayscale alignment references.
3. `src/components/GalaxyPopup.tsx` displays one galaxy's **distance_from_us**
   value. `ComparisonPanel.tsx` displays the four exported values for a pair.
   The data adapter indexes all pairs by an unordered ID key and swaps the two
   radial distances when the user reverses A/B. No distances are computed in JS.
4. `src/App.tsx` owns Inspect/Compare mode, pending A, completed A/B, and close/
   Escape behavior. `src/data/markerLayout.ts` handles viewport-dependent culling.
   `src/components/InfoTip.tsx` contains the scientific glossary and accessible
   hover/focus/tap tooltips.
   `GalaxySearch.tsx` provides an accessible combobox over every eligible record.
   `src/styles.css` controls all appearance and responsive layouts.

`distance_from_us` has a numeric value (or null), unit `ly`, and convention
`comoving`. The popup uses readable million/billion light-years, states Planck18
from the export, and retains the full galaxy ID. It shows RA and Dec in ICRS
degrees, redshift, quality, and numerical redshift uncertainty when available;
the current catalog's null uncertainty is labeled **not published**. The distance
is a model-based comoving estimate, distinct from light-travel time. Quality
flags are identification categories, not percentages or distance error bars.

To update the exports, run from the repository root:

```powershell
.\my_venv\Scripts\python.exe run_starmap.py
.\my_venv\Scripts\python.exe -m starmap.imaging
```

Development imports refresh automatically when files change. Rebuild production
output after changing exports. No manually copied frontend data snapshot needs
to be kept in sync. Keep `frontend/` beside `results/` in the source checkout.

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
`goods-s-deephst:21842` and looks up their existing exported measurements. No
measurements are hard-coded. Empty-sky releases, a drag
back to the starting galaxy, or selecting A twice cancel the unfinished pair.
Escape and Clear comparison reset it. Clicking the already active Inspect or
Compare mode does nothing; switching between different modes still clears the
selection. Resizing keeps selections pinned. Amber rings and a line identify
the comparison. The line is angular separation on the sky, while the exported
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

Install the test browser once, then run the suite:

```powershell
npx playwright install chromium
npm test
```

The suite clicks/taps all currently visible galaxies in desktop and mobile contexts,
checks that popup IDs, distances, coordinates, redshifts, and uncertainty status
match the JSON exports, and verifies selection replacement, close, Escape,
keyboard access, and restored focus. It checks every marker's position relative
to the image at 1440, 768, 390, and 320 pixel viewport widths, including the
actual browser transform and circle geometry. Tests compare the same non-original
pair by desktop pointer drag and mobile taps against all four exact JSON values,
check reverse order and cancellation, and verify tooltip hover/focus/tap behavior.
Priority tests cover quality, apparent size, missing-size ID fallback, stable
ordering, and the reason every hidden marker was suppressed.
Additional checks inspect every normally hidden galaxy through search, exercise
combobox keyboard navigation, mix map/search selections, compare the example
pair, preserve active-mode selections, and verify that phones download one
appropriately sized color WebP while grayscale waits for its toggle.

The archived original sample has all 105 pairs. A development-only test fixture
at `tests/fixtures/prototype1.html` mounts this same App with those 15 galaxies;
it is not part of the production build. The expanded default has all 903 pairs.

Backend tests independently check per-galaxy distance exports, unknown distances,
and native PNG dimensions and row orientation. The original WCS and calculation
checks remain in `starmap.verify`. Visual reference artifacts are in `results/`.
The saved `results/frontend_prototype2_desktop.jpg` and
`results/frontend_prototype2_mobile.jpg` show the same comparison on desktop and
mobile. Earlier `frontend_desktop.jpg` and `frontend_mobile.jpg` preserve the
Prototype 1 inspector previews.

Vercel's two-service setup and optional read-only export API are documented in
the root README. This browser app still imports the exports directly and has no
runtime service calls or binding environment variables. Additional fields,
redshift-error propagation, and a live calculation API remain later milestones.
