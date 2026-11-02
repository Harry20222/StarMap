# Frontend Prototype 1: GOODS-S field explorer

Select a ring on the real JADES GOODS-S three-filter color image to inspect one galaxy.
The selectable set is derived from the backend exports, including galaxies
outside the three backend example pairs. There are currently 15 quality-A objects.
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
2. `src/components/GalaxyMap.tsx` displays the static `results/goods_s_color.png`
   and interactive rings in one SVG. Real JADES DR2 F090W, F200W, and F444W SCI
   observations map to blue, green, and red. The color image has exactly the same
   grid as the native 2,000 × 2,000 F200W reference crop, without axes or baked-in
   markers. `results/goods_s_f200w.png` and `results/galaxy_map.png` remain the
   original grayscale alignment references.
3. `src/components/GalaxyPopup.tsx` displays the selected record and its
   **distance_from_us** value. It never calculates a cosmological distance or
   tries to recover individual distances from the three pair records.
4. `src/App.tsx` owns the single selection and Escape/close behavior.
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

Rings have no fill and a thin visible stroke. Invisible hit circles provide
44-pixel touch areas where possible. Dense regions can have overlapping hit
areas: a pointer event selects the nearest actual galaxy center rather than
relying on paint order. Keyboard users can Tab to each ring and press Enter or
Space. Only one galaxy is selected; amber rings mark it. Escape or Close dismisses
the inspector and restores marker focus. On phones the inspector follows the
map and scrolls into view, keeping the image unobstructed.

The color asset is generated once, not at runtime. To regenerate it from the
repository root, run `python -m starmap.color_image` with the project environment.
The first run retrieves matching WCS-based F090W/F444W crops from MAST; later runs
reuse `data/cache/color/`. The existing F200W cutout is the alignment reference.
Background subtraction, channel balance, and a shared-intensity Lupton asinh
stretch reveal faint sources while compressing bright cores. These display
adjustments do not change any catalog, marker, or distance. Source URLs, hashes,
registration checks, and exact rendering settings are in `results/goods_s_color.md`.

## Verification

Install the test browser once, then run the suite:

```powershell
npx playwright install chromium
npm test
```

The suite clicks/taps all selectable galaxies in desktop and mobile contexts,
checks that popup IDs, distances, coordinates, redshifts, and uncertainty status
match the JSON exports, and verifies selection replacement, close, Escape,
keyboard access, and restored focus. It checks every marker's position relative
to the image at 1440, 768, 390, and 320 pixel viewport widths, including the
actual browser transform and native PNG dimensions. Data-join checks shuffle
records, change the quality-A count, and reject missing or duplicate IDs.

Backend tests independently check per-galaxy distance exports, unknown distances,
and native PNG dimensions and row orientation. The original WCS and calculation
checks remain in `starmap.verify`. Visual reference artifacts are in `results/`.
The saved `results/frontend_desktop.jpg` and `results/frontend_mobile.jpg` show
the selected-galaxy inspector on desktop and mobile, respectively.

Comparing two selected galaxies, extra catalogs, redshift-error propagation,
and an API service are later milestones.
