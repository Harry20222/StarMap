# StarMap: JADES galaxy distances

A Python backend and React/TypeScript field explorer for learning to match JWST
images to galaxy catalogs and measure distances with Astropy's **Planck18** cosmology. The bundled
sample contains **43 deduplicated JADES galaxies with flag-A spectroscopic redshifts**
inside the same GOODS-S cutout. All **903 unique pairs** are exported for the
frontend; the original three regression pairs are still printed in the terminal.
Calculations and the frontend run without a Python API server.

## Requirements and scope

The prototype implements the current Python milestone:

- Match separate image and catalog products using celestial coordinates and the
  image WCS, retaining galaxy IDs, redshifts, quality flags, and source metadata.
- For each selected pair, print and export angular separation in degrees,
  comoving distance from us to A and to B in light-years, and their estimated
  comoving 3D separation in light-years.
- Use Planck18 consistently, keep quality flags separate from numerical errors,
  and explicitly represent missing reliable distance information as unknown.
- Make pair selection editable by galaxy ID. Separate loading, selection,
  calculations, and output; provide a CLI and cached source retrieval.
- Verify source rows, image positions, and calculations; include meaningful tests.

Frontend Prototype 2 provides **Inspect** and **Compare** modes. Inspect opens the
existing single-galaxy popup. Compare lets you drag between two visible rings or
select two in sequence by click, tap, or keyboard. The panel identifies A and B
and displays angular separation, each galaxy's comoving distance from us, and
estimated 3D comoving separation, all from the Python/Astropy Planck18 exports.
Scientific terms have circled, superscript-style information buttons that work
on hover, keyboard focus, and mobile tap.

The original 15-galaxy dataset is retained as `data/prototype1_sample.json`, with
all 105 pairs in `results/prototype1_measurements.json`. A browser fixture tests
the same comparison UI against this original sample before the expanded data.

## Frontend: open the field explorer

The frontend is in `frontend/` and uses React, TypeScript, CSS, and Vite. It
imports the backend JSON files and derived display images directly; **no Python API server
is needed**. Node.js 20.19+ or 22.12+ is required (Node 24 was used here).

First-time setup, from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Local URL printed by Vite. For subsequent runs, open **`run_frontend.py`**
in your editor and press **Run**. It starts the Node/Vite preview and opens your
browser; stop the script to stop that preview. This launcher is optional and
does not run a Python web server. `run_starmap.py` still runs the backend exports.

Thin green rings identify visible quality-A galaxies. Apparent F200W half-light
radii from the documented DR2 photometric catalog rank equally reliable galaxies
when rings would overlap. The layout is recomputed at the current display size,
including room for selected outlines. **Find a galaxy** searches every ID,
including galaxies whose rings are hidden. Search results work with click/tap,
Arrow keys, and Enter. Selected rings always appear at their actual coordinates,
and other colliding rings are hidden. Two close selected rings may overlap;
both IDs remain visible in the comparison panel.
The legend reports visible and total counts (for example, about 39 on desktop
and 28 on a 390-pixel phone viewport, out of 43 records). Counts can vary with width.
A selected galaxy gets a distinct amber outline.
Click another ring to update the inspector, or dismiss with its close button or
Escape. Tab and Enter/Space also select markers. On small screens, the inspector
appears below the image and scrolls into view without covering the other rings.
In Compare mode, select A and B using the map, search, or a mixture of both.
**Try an example pair** selects 21598 and 21842 using their existing exported
measurements. Dragging to empty sky or back onto the starting ring cancels the
unfinished line. Selections remain visible through resizing. Clicking the active
mode does nothing; switching modes and the intentional clear controls reset it.
The drawn line represents separation on the sky; the 3D estimate also uses both
galaxies' radial comoving distances. Escape or Clear comparison resets the pair.

To refresh data or imagery after backend changes, run these from the repo root:

```powershell
.\my_venv\Scripts\python.exe run_starmap.py
.\my_venv\Scripts\python.exe -m starmap.imaging
```

Vite notices changes to the imported files during development. A production build
must be rebuilt after exports change. From `frontend/`, `npm run build` creates
the self-contained static site in `dist/`; `npm run preview` serves that build.
The image, fonts, and catalog data are bundled locally. Use a static HTTP server
to view the build rather than double-clicking its HTML file.

The map uses 640/1280/2000-pixel WebP variants generated once from the unchanged
PNG cutouts. Image resolution follows the actual map width and pixel density;
the SVG coordinate system stays fixed. Grayscale bytes are fetched only after
the user chooses that mode. Regenerate variants with
`python frontend/scripts/export_map_images.py` after updating the source PNGs.

See `frontend/README.md` for component structure, data flow, and browser tests.

## Vercel deployment

The root `vercel.json` proposes two services in one Vercel project. Confirm the
service names and public exposure before deploying:

- **frontend**, rooted at `frontend/`, builds with `npm ci` and `npm run build`,
  and serves `dist/`. The catch-all public rewrite sends `/` and static asset
  requests here.
- **app**, rooted at the repository root, uses the Python WSGI entrypoint
  `app:app`. Public `/api` and `/api/*` requests go here, preserving the original
  path prefix. Its read-only routes are `/api/health`, `/api/markers.json`, and
  `/api/measurements.json`; `/api` lists the exports. Unknown API routes return
  JSON 404 responses, and writes return 405. This adapter serves the existing
  export bytes; generating datasets remains a local/offline operation.
  `python app.py` is the service's explicit development command; it listens on
  the `PORT` injected by `vercel dev`. Production loads the WSGI callable.

**No inter-service bindings are declared.** The React app imports the JSON files
at build time and makes no runtime HTTP calls to Python; neither service calls
the other. The local `127.0.0.1` addresses belong only to the development launcher
and browser tests. Public MAST URLs identify observation sources. None is an
internal service address to replace. A binding would belong on a future
server-side caller, with its URL read at function runtime; do not introduce a
`VITE_*` binding or set a binding URL manually. See Vercel's
[service bindings documentation](https://vercel.com/docs/services/bindings).

Keep the Vercel **project Root Directory at the repository root (`.`)** so the
root services config and shared `results/` assets are available; the frontend
service has its own root. Use Node.js 24 for the frontend. Python's supported
runtime version is selected from the existing `pyproject.toml` constraints.
No environment variables or secrets are required by the current services.

To test both services and the public routing together from the repository root,
use the current Vercel CLI:

```powershell
npx vercel@latest dev --local
```

`--local` is Vercel's unauthenticated local mode. With a linked project, use
`npx vercel@latest dev` instead. The command reports the local URL. Verify `/`
loads the map, both image modes work, and `/api/health`, `/api/markers.json`, and
`/api/measurements.json` respond. `/api/missing` should return JSON 404 rather
than the frontend page. The website continues to use the bundled exports, so
commit regenerated JSON and rebuild when the data changes.

On this Windows machine, Vercel CLI 65.11.0's native builder installer failed
with `EPERM` creating symlinks. Its bundled JavaScript CLI successfully ran the
combined preview. For the same issue, select that fallback for the current
PowerShell session:

```powershell
$env:VERCEL_CLI_USE_NATIVE_BINARY = "0"
npx vercel@latest dev --local
```

To undo the temporary choice, run
`Remove-Item Env:VERCEL_CLI_USE_NATIVE_BINARY`. No Windows permission changes
are needed for this workaround.

Validation: `tests/test_web.py` checks WSGI conformance, exact export bytes,
HEAD, method rejection, and prefixed routes. The production frontend build
passes. Combined `vercel dev --local` checks returned 200 for `/`, `/api`,
`/api/health`, and both exports, plus JSON 404 for `/api/missing`.

After confirming names, routing, and bindings, import this repository into one
Vercel project or deploy from its root with the CLI. The deployment config keeps
build/runtime options inside each service and public rewrites at the top level,
as required by [Vercel Services](https://vercel.com/docs/services). The Python
function explicitly includes the two exports and excludes frontend/image/data
files from its runtime bundle. `.vercelignore` also omits local environments,
caches, test fixtures, and review screenshots from CLI uploads, while retaining
both real map PNGs and the two current exports for the frontend build.

The top-level response headers set **Content-Security-Policy:
`frame-ancestors 'none';`**, since the portfolio only links to StarMap. A separate
rule applies **Cache-Control: `public, max-age=31536000, immutable`** only to
Vite-generated `/assets/<name>-<8-character-hash>.<extension>` paths. The homepage,
stable filenames, and read-only `/api` responses stay outside the immutable rule.
Existing public routes and API behavior are preserved.

After deploying, check the actual response headers on the live domain with
`curl.exe -I https://starmap-rkdg.vercel.app/` and on one newly emitted hashed
WebP/JS asset (use its exact filename from `frontend/dist/assets/`). Confirm CSP
is present, hashed assets receive immutable caching, and `/`, `/index.html`,
and `/api/measurements.json` do not receive immutable caching. Local config and
development-server checks do not establish what the production CDN returns.
In the checked Vercel CLI 65.11.0 services preview, the top-level CSP/cache header
overrides were not emitted. Vercel's own route compiler did validate the cache
matcher against all 40 generated assets and reject the homepage, API, and stable
asset names. Check the actual headers after deployment rather than treating the
development preview as proof of CDN behavior. The embedding directive is
documented in [MDN's frame-ancestors reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).

## Install and run

Python 3.11+ is supported by the dependency declarations. The checked environment
used Python 3.14.3, Astropy 8.0.2, NumPy 2.5.4, SciPy 1.18.1, Matplotlib 3.11.2,
fsspec 2026.9.0, and pytest 9.2.0. Dependencies are declared in `pyproject.toml`.

From the repository root in PowerShell:

```powershell
py -m venv my_venv
.\my_venv\Scripts\python.exe -m pip install -e ".[dev]"
.\my_venv\Scripts\python.exe -m starmap
.\my_venv\Scripts\python.exe -m pytest -q --basetemp .pytest_cache\tmp
```

The Windows examples use `my_venv`; reuse the existing environment if it is
already installed. On macOS/Linux use `python3 -m venv my_venv` and
`my_venv/bin/python`.
After installation, `starmap` is also available in the environment's Scripts/bin
directory. Run commands from the repository root, or pass explicit data paths.

The default run writes `results/measurements.json`. The bundled `data/sample.json`
is sufficient for calculations; no image download is required to calculate pairs.
The native FITS cutout and parent WCS header are included for offline verification.

### Run a single file

After installing dependencies, open `run_starmap.py` in your editor, select the
Python interpreter from `my_venv`, and press **Run**. No terminal command is
needed. It prints the measurements for the three pairs in `data/pairs.json` and
saves **all 903 pair results** in `results/measurements.json`. Data paths are resolved relative to the script,
so the editor's working directory does not matter. Keep the rest of the project
files alongside the launcher; it uses the existing modules and bundled data.

```powershell
# Export a custom pair to a separate file; --pair can be repeated.
.\my_venv\Scripts\python.exe -m starmap --pair goods-s-deephst:17160 goods-s-deephst:19607 --output results\custom.json

# Rebuild finding charts and perform independent numerical/WCS checks.
.\my_venv\Scripts\python.exe -m starmap.imaging
.\my_venv\Scripts\python.exe -m starmap.verify

# Optional: retrieve/cache original source files and rebuild the sample.
.\my_venv\Scripts\python.exe -m starmap.prepare
```

Edit `data/pairs.json` to change the terminal regression examples. The normal
JSON export still contains every unique pair. `--pair` explicitly restricts an
export, so use `--output results/custom.json` to preserve the full frontend data.
IDs use `TIER:NIRSpec_ID`;
all available IDs and metadata are in `data/sample.json`. An unknown ID produces
a clear CLI error. The `--sample`, `--pairs`, and `--output` options accept custom
paths. `python -m starmap --help` lists options.

## Dataset and provenance

Sources are the [official JADES MAST archive](https://archive.stsci.edu/hlsp/jades),
its [product documentation](https://archive.stsci.edu/hlsps/jades/hlsp_jades_readme.txt),
the [DR3 paper](https://arxiv.org/abs/2404.06531), and the
[DR2 imaging paper](https://arxiv.org/abs/2310.12340).

- Spectroscopy: JADES **DR3**, GOODS-S prism line-flux catalog **v1.1**, FITS
  extension 1, 2,525 rows.
  [Download catalog](https://archive.stsci.edu/hlsps/jades/dr3/goods-s/catalogs/hlsp_jades_jwst_nirspec_goods-s_prism-line-fluxes_v1.1_catalog.fits).
  `z_Spec` is the combined best spectroscopic redshift, even though this is the
  prism flux table. Positions are `RA_NIRCam`, `Dec_NIRCam` in ICRS degrees.
- Image: JADES **DR2 v2.0**, GOODS-S, **JWST/NIRCam F200W**, `SCI` extension.
  [Download parent mosaic](https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/hlsp_jades_jwst_nircam_goods-s-deep_f200w_v2.0_drz.fits).
  The parent product is about 11 GB; the bundled native 2,000 × 2,000 pixel crop
  is about 16 MB and spans approximately 60 arcseconds. Pixel scale is
  approximately 0.0299947 arcsec/pixel; the FITS WCS is authoritative.
- Fixed center: RA 53.160622050813075°, Dec −27.771611286298103°.
  Crop indices in the parent `SCI` array are
  `SCI[19816:21816, 6905:8905]` (Python's zero-based, end-exclusive indexing).
- Selection: all tiers, flag A, positive finite `z_Spec`, no `DR_flag`, valid
  NIRCam match and coordinates inside the existing image's pixel-center bounds.
  There are 45 eligible observations and 43 unique NIRCam IDs. Deduplicate by
  NIRCam ID, retain previously published prototype IDs, and otherwise choose the
  lexicographically first `TIER:NIRSpec_ID`. The recipe is in `starmap/prepare.py`;
  all 43 full records and source row indices are saved.

Apparent sizes use `SIZE.F200W_RHALF`, the **circularized half-light radius in
arcseconds**, from the [DR2 v2.0 photometric catalog](https://archive.stsci.edu/hlsps/jades/dr2/goods-s/catalogs/hlsp_jades_jwst_nircam_goods-s-deep_photometry_v2.0_catalog.fits).
The [extension documentation, page 5](https://archive.stsci.edu/hlsps/jades/hlsp_jades_jwst_nircam_goods-s-deep_photometry_v2.0_catalog-ext-readme.pdf)
defines the measurement. Check ID matches on the sky within 0.2 arcsec; if
re-segmentation changed an ID, use the nearest spatial match within that limit
and retain the size catalog's ID separately. All 43 sources currently have
positive comparable radii. Missing or invalid sizes remain null; they are not
estimated from brightness. Source URLs, matches, metric names, and cache hash are
recorded in the exports. `starmap/sizes.py` handles this optional preparation step.

Marker visibility prioritizes redshift quality first, then the larger comparable
apparent radius. Equal or incomparable sizes use the full galaxy ID as a stable
tie-breaker. A deterministic greedy pass retains a maximal non-overlapping set;
it preserves the larger-priority object even when several smaller neighbors
could otherwise fit. Explicit selections are pinned first; only two selected
rings may overlap. Marker ring diameters are display aids, not galaxy sizes.

The catalog already supplies NIRCam matches within 0.2 arcsec. Compatibility is
checked spatially against the DR2 GOODS-S image, rather than by assuming matching
release numbers or equating NIRCam IDs with NIRSpec IDs. NIRSpec IDs can repeat
between tiers, so both fields identify a spectrum. This fixed teaching dataset
uses archival DR3 redshifts; **DR4 supersedes most DR3 spectroscopy**.

Documented flags, paraphrased from the product documentation:

- **A:** highly robust, emission lines with S/N > 5 in R~1000 grating data.
- **B:** highly robust, emission lines with S/N > 5 in Prism/Clear data.
- **C:** secure identification from spectral breaks and/or weak emission lines.
- **D:** tentative redshift.
- **E:** no redshift.

The sample uses only A. The general calculation API accepts A/B as reliable;
C/D/E and unrecognized/missing flags yield unknown radial distances. This is a
conservative application policy, not a reinterpretation of the published flags.
The selected table has **no published `z_Spec` numerical uncertainty column**.
`redshift_uncertainty` is therefore `null` with an explicit status. Emission-line
flux uncertainties are not redshift errors. Flags never become percentages or
numerical error bars.

`data/sample.json` and every measurements export retain source URLs, releases,
column names, row indices, IDs, quality meanings, crop geometry, and SHA-256
checksums. Source downloads are cached in ignored `data/cache/`; repeated runs
reuse them. Catalog preparation rejects a changed source checksum. If the cutout
must be regenerated, Astropy/fsspec reads HTTP byte ranges from `SCI`, transferring
roughly a 200 MB row span instead of the entire mosaic. The source documentation
is also cached. Calculation functions never download data.

## Scientific assumptions

All lengths are **comoving distances**, using scale factor `a0 = 1`, expressed
in light-years (`ly`, converted with Astropy's `u.lyr`). They are distinct from
light-travel time, luminosity distance, angular-diameter distance, and proper
distance at the epoch when the observed light was emitted. Values above the
Universe's age expressed in years are expected for this distance convention.

The model is the actual Astropy `Planck18` realization, a flat ΛCDM cosmology with
H0 = 67.66 km/s/Mpc, Ωm = 0.30966, Ωb = 0.04897, Tcmb = 2.7255 K, Neff = 3.046,
and neutrino masses [0, 0, 0.06] eV. The output records these parameters and the
Astropy version. See [Astropy's Planck18 documentation](https://docs.astropy.org/en/stable/api/astropy.cosmology.realizations.Planck18.html).

For two sky directions separated by θ, first obtain radial comoving distances
`rA = Planck18.comoving_distance(zA)` and `rB` from Astropy. Since Planck18 is
spatially flat, the estimated 3D comoving chord length is

```text
d = sqrt((rA - rB)^2 + 4*rA*rB*sin(θ/2)^2).
```

This numerically stable form includes the transverse component. Merely
subtracting radial distances would miss it. `SkyCoord.separation` computes θ on
the sphere, accounting for declination and RA wrapping.

These are **model-based redshift-space estimates**. Peculiar velocities,
gravitational effects, cosmological parameter errors, and measurement errors
are not corrected or propagated. A 3D separation is not evidence that two
galaxies are interacting or bound. The galaxies are seen at different emission
epochs; the calculation places their inferred positions in the same comoving
coordinate system, rather than measuring an instantaneous observed physical
distance. Extra decimal places support reproducibility, not claimed accuracy.

Missing coordinate values or unreliable/missing redshifts produce `null` for
the affected measurements and explicit `unknown_reasons`. Valid angular or
individual radial distances remain available when possible. Malformed numbers,
nonfinite values, negative redshifts, RA outside [0,360), and Dec outside [-90,90]
raise `ValueError`; the catalog loader filters invalid/sentinel/masked rows.

## Three original regression pairs

Every ID below has tier `goods-s-deephst` and quality A. These are illustrative
comparisons, not claims of physical association. Terminal values are rounded
for display; the JSON retains the calculated floating-point values.

```text
17160 (z=1.8502956189914272) ↔ 19607 (z=1.8474041908000198)
  angular separation:          0.006431248882 deg
  comoving distance to A:      1.656984581e10 ly
  comoving distance to B:      1.655496638e10 ly
  estimated comoving 3D:       1.499511073e7 ly

17566 (z=6.101533511321096) ↔ 19342 (z=5.974287172942812)
  angular separation:          0.005852644316 deg
  comoving distance to A:      2.761895798e10 ly
  comoving distance to B:      2.744307634e10 ly
  estimated comoving 3D:       1.759041184e8 ly

16996 (z=2.7754479844376094) ↔ 21842 (z=7.980506972822209)
  angular separation:          0.01049947532 deg
  comoving distance to A:      2.046811462e10 ly
  comoving distance to B:      2.976558133e10 ly
  estimated comoving 3D:       9.297467810e9 ly
```

## Image and calculation verification

`results/galaxy_map.png` labels all 43 positions. `results/alignment_stamps.png`
shows 3-arcsec stamps with open rings, preserving source visibility. Visual
inspection is recorded in `results/alignment_review.md`; some targets are faint
in this single filter. Dark masked regions in the mosaic are not sky structures.
`results/goods_s_f200w.png` is the original clean, unannotated 2,000 × 2,000
grayscale reference, with pixel rows flipped for top-left browser coordinates.
The frontend displays static WebPs derived from `results/goods_s_color.png`: real JADES DR2
F090W → blue, F200W → green, and F444W → red, registered to exactly the existing
F200W cutout's WCS and pixel grid. The caption identifies these assigned colors.
Generate this asset only when needed with `python -m starmap.color_image`; the
website performs no image processing. Registration, source URLs, and display
settings are recorded in `results/goods_s_color.md`. The grayscale images remain
available for alignment checks, and all catalog JSON and marker coordinates are
unchanged by color generation.

`starmap.verify` checks every source row when the original catalog is cached,
the bundled image checksum, all marker bounds, sky/pixel roundtrips, and parent
pixel coordinates minus the exact crop origin. Parent/crop residuals are below
10⁻⁶ pixel; this verifies cropping in addition to a self-consistent WCS.

For all three pairs, a separate implementation integrates `1/E(z)` on an
8,192-interval grid using Simpson's rule, computes the angle from unit-vector
cross/dot products, and subtracts Cartesian position vectors. It uses
`Planck18.efunc` to retain the same neutrino/expansion model, but does not call
Astropy's comoving-distance integrator or sky-separation routine. All four
measurements agree to better than 10⁻¹² relative difference in the checked run
(acceptance tolerance 10⁻⁸). This validates the implementation, not astrophysical
accuracy. Details are in `results/verification.json`.

Tests cover swapping, self-comparison, equal-redshift transverse distances,
same-direction radial differences, right-angle geometry, RA wrapping and poles,
missing/invalid data, quality versus uncertainty, independent calculations,
catalog filtering, crop/scale WCS mapping, ID validation, and CLI JSON export.

## Code and JSON integration

- `models.py`: validated galaxy records and documented quality semantics.
- `data.py`: cached downloading, source parsing, JSON I/O.
- `prepare.py`: reproducible sample and native image cutout preparation.
- `selection.py`: pair lookup by full ID.
- `calculations.py`: pure angular/radial/3D calculations.
- `output.py`, `cli.py`: versioned JSON schema and terminal interface.
- `imaging.py`, `verify.py`: scientific finding charts and verification.

```python
from starmap import Galaxy, measure_pair

a = Galaxy("A", ra_deg=53.16, dec_deg=-27.77, redshift=2.0, redshift_quality="A")
b = Galaxy("B", ra_deg=53.17, dec_deg=-27.78, redshift=2.1, redshift_quality="A")
measurements = measure_pair(a, b)  # Independent of any downloading or file layout.
```

The results object contains `schema_version`, `cosmology`, `distance_convention`,
`dataset`, `galaxies`, and `pairs`. Each measurement has a numeric `value` (or
`null`) and `unit`; lengths have `convention: "comoving"`. Galaxy metadata carries
quality and uncertainty separately. Schema 1.1 also adds `distance_from_us` to
**every** galaxy record, independently of the three selected test pairs, with
`value`, `unit: "ly"`, and `convention: "comoving"`; unavailable distances stay
`null`. The exported `results/markers.json` uses
zero-based pixel centers with a bottom-left origin. The frontend uses
`y_top = height - 1 - y` and places both the image and rings in one SVG viewBox,
so they resize together. The annotated
PNG has plot margins and axes: its full canvas dimensions must not be treated as
the raw FITS image dimensions. The UI uses display WebPs derived from the clean
pixel-only PNGs, preserving their full extent and orientation.

Schema 1.2 additionally records the optional apparent-size fields and exports
every unique pair by default: n(n−1)/2 results for n records. There are 105 for
the archived initial sample and 903 for the expanded sample. The frontend joins
records by full ID and looks up Python-calculated pairs, swapping A/B radial
distances when the user chooses the reverse order; it does not recompute cosmology.

## Data attribution

JADES HLSP products are provided under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Data DOI: [10.17909/8tdj-8n28](https://doi.org/10.17909/8tdj-8n28).
Credit the JADES collaboration, D'Eugenio et al. (DR3 spectroscopy), and
Eisenstein et al. (DR2 imaging), as linked above. These data are based on
NASA/ESA/CSA JWST observations obtained through MAST at STScI, operated by AURA
under NASA contract NAS 5-03127. Consult the source papers/archive for the full
acknowledgements when using the products in research.
