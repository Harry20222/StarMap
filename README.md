# StarMap: JADES galaxy distances
# NOTE: This version has been deployed but version shown on my website is one from main branch
https://starmap-git-testing-me-5037.vercel.app/
StarMap is a React/TypeScript field explorer with a read-only Python WSGI API.
The website loads the GOODS-S map and **43 quality-A galaxies from MongoDB**.
The backend uses the unchanged Astropy **Planck18** functions to calculate a
comparison only when requested. Images remain static WebP assets.

The existing JSON files remain migration sources and regression fixtures,
including all **903 unique pairs**. The production browser does not import them
and displays an error with Retry if the API/database is unavailable.

## Local setup and migration

Use Python 3.11+ and Node.js 20.19+ or 22.12+ (tested here with Node 24).
From the repository root in PowerShell, reuse the existing `my_venv` or create it:

```powershell
py -m venv my_venv
.\my_venv\Scripts\python.exe -m pip install -e ".[dev]"
# Only if .env does not already exist:
Copy-Item .env.example .env
```

Set **both** `MONGODB_URI` and `MONGODB_DATABASE` in `.env`. There is no default
database name. Existing process environment values override `.env`; never
prefix these settings with `VITE_`. `.env` and `.env.*` are ignored by Git and
excluded from Vercel uploads/function bundles. `.env.example` has empty placeholders.
Do not overwrite an existing `.env` when following setup instructions.

```powershell
.\my_venv\Scripts\python.exe connect_mongodb.py
.\my_venv\Scripts\python.exe migrate_mongodb.py --validate-only
.\my_venv\Scripts\python.exe migrate_mongodb.py
# Repeat to verify idempotence: inserted and modified counts should be zero.
.\my_venv\Scripts\python.exe migrate_mongodb.py
# Read-only check of every imported field and all 903 API comparisons:
.\my_venv\Scripts\python.exe verify_mongodb.py
```

The importer validates source/export metadata and unique IDs, all 43 quality-A
records, finite coordinates, null meanings, image dimensions, FITS checksum,
and every marker's WCS projection **before writing**. It preserves catalog
versions, source row indices, separate NIRSpec/NIRCam/size-catalog IDs, ICRS
degrees, redshift uncertainty status, and F200W half-light radii in arcseconds.

Collections:

- `galaxies`: full stable `galaxy_id`, catalog fields, uncertainty/size metadata,
  and catalog provenance. Individual distances are calculated by Python on reads.
- `maps`: stable `map_id` **`goods-s`**, dataset/cosmology metadata, original image
  references and static variant names, shape `[2000, 2000]`, serialized celestial
  WCS, crop geometry, coordinate frame/units, and browser coordinate conventions.
- `map_markers`: `map_id`, `galaxy_id`, original `x`, `y`, inside-image status,
  and roundtrip residual. One galaxy can have different positions in other maps.

Unique indexes protect galaxy IDs, map IDs, and `(map_id, galaxy_id)` memberships.
Scoped `$set` upserts retain unrelated records, collections, and extra fields.
The importer never drops collections, deletes records, or stores images/pair tables.
It refuses unexpected markers on this specific map instead of removing them.
The import is rerunnable after interruption; it is not a multi-document transaction.
Run it before enabling a new map publicly. Verification checks the exact expected
43 IDs, all source metadata and nulls, and every original marker double.

## Run the website

Start Python from the repository root:

```powershell
.\my_venv\Scripts\python.exe app.py
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite Local URL. Vite proxies `/api` to `http://127.0.0.1:8000` without
removing the prefix. For a different local Python port set `PORT` on Python and
`STARMAP_API_PROXY` on Vite. This optional proxy setting is a development server
address, not a browser credential. `run_frontend.py` starts the Vite browser preview;
start Python separately. `npm run build` in `frontend` performs the TypeScript
check and creates `dist/`. For `npm run preview`, keep Python running; the same
proxy is configured for that local preview. Production requires both services.

Inspect/Compare modes, search including hidden rings, size-based overlap handling,
drag/click/tap/keyboard selection, the example pair (21598/21842), scientific
explanations, color/grayscale switching, and mobile layouts retain their behavior.
Selected galaxies stay pinned at their true coordinates. Metadata still specifies
zero-based **pixel centers**, lower origin, and `y_display = height - 1 - y`.
The image and overlay share a viewBox beginning at `-0.5`, preserving alignment.
Loading, empty and failure states provide Retry; failed comparisons retain the
selection and offer Retry comparison. Aborted/older requests cannot replace newer
selections. Fetching and joining live data are separate from display components.

## Read-only API

All routes accept GET/HEAD; other methods receive JSON 405:

- `/api`: route discovery.
- `/api/health`: database ping; 503 when unavailable.
- `/api/maps`: available map summaries.
- `/api/maps/goods-s`: selected map metadata and static image references.
- `/api/maps/goods-s/galaxies`: galaxies with current per-galaxy Python distances
  and their original map-specific marker positions. Contains no pair table.
- `/api/maps/goods-s/compare?a=goods-s-deephst%3A21598&b=goods-s-deephst%3A21842`:
  Python/Astropy comparison in the requested A/B order.

Only specific validated IDs and exact parameters are accepted. Both galaxies
must belong to the map. Invalid IDs/parameters or self-comparisons return 400;
unknown maps, nonmembers and missing galaxy records return 404; incomplete or
malformed stored catalogs return 500; database/configuration failures return 503
with Retry-After. Driver diagnostics/credentials are never returned. Responses
use `Cache-Control: no-store`. The former export-serving routes return 404.

Angular separation stays in **degrees**; individual radial comoving distances
and estimated **3D comoving separation** stay in **light-years**. Missing
coordinates/redshifts or qualities outside A/B produce null affected measurements
and explicit reasons. Valid unaffected measurements remain available. Uncertainty
is not propagated; quality flags never become numeric error bars.

## Vercel deployment and database permissions

The existing two-service `vercel.json` routing is retained: `/api` and `/api/*`
go to Python `app:app` with the original prefix; all other requests go to the
Vite frontend. Keep the Vercel project Root Directory at the repository root.
Python's base `pyproject.toml` dependencies now include PyMongo, DNS/SRV support,
python-dotenv, and the scientific runtime; deployment does not require an optional
MongoDB extra. Python bundles `starmap/**` and excludes images, exports, test data,
local environments and `.env` files. Static assets stay in the frontend build.
[Vercel Python dependency documentation](https://vercel.com/docs/functions/runtimes/python).

Configure **`MONGODB_URI` and `MONGODB_DATABASE` on the Python `app` service** for
Production and any Preview/Development environments that should access the catalog.
Use the selected database's name explicitly and a URI preserving authentication/TLS
options. Redeploy after changing runtime settings. Do not put these variables on
the frontend service or expose a `VITE_*` version. The Python process lazily reuses
one pooled PyMongo client with bounded connection, selection, socket, pool wait,
and operation timeouts. [MongoDB client documentation](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/mongoclient/).

Use separate MongoDB users:

- **Migration operator:** `readWrite` on the selected database (including createIndex).
  Run the migration locally with this credential. It is not needed by the website.
- **Public Python service:** `read` on that database, or a custom role limited to
  reads on `maps`, `galaxies`, and `map_markers`. The API never creates indexes or
  writes data. Give preview deployments equivalent read-only access if enabled.

Allow the Python service's network traffic in Atlas using your deployment's
network configuration. Test `/api/health`, map list/catalog and a comparison after
redeploying. No live deployment is performed by the import scripts. Existing CSP
`frame-ancestors 'none'` and immutable caching for hashed static assets are unchanged.
Confirm actual response headers and routing on the deployed domain.

For combined local Vercel routing, use `npx vercel@latest dev --local` from the root
(or `npx vercel@latest dev` with a linked project). On Windows, if its native builder
fails creating symlinks, `$env:VERCEL_CLI_USE_NATIVE_BINARY = "0"` selects the JS CLI.

## Automated verification

```powershell
.\my_venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
cd frontend
npx playwright install chromium
npm test
npm run build
```

Backend and browser tests use fresh **mongomock databases**, never `.env` or the
selected live database. Browser tests start the actual WSGI API on port 8001 and
Vite on 5173 with an isolated proxy. Set `STARMAP_TEST_PYTHON` to the Python
interpreter with `.[dev]` installed if auto-detection does not fit your environment.
Stop other servers on these test ports first. The database failure check uses
a closed loopback port with a short timeout.

Checks cover migration idempotence, unique indexes, preservation of unrelated data,
all 43 records/positions/nulls, all **903 WSGI comparisons** at `1e-10` relative
and `1e-12` absolute tolerance, missing records, membership, invalid IDs,
unavailable distances, connection/configuration failures, and desktop/mobile
search, pointer/keyboard selection, overlaps, image alignment and retry behavior.
`verify_mongodb.py` separately runs read-only verification against the configured
real database. JSON fixtures are unchanged and available for offline science.

## Offline scientific exports

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
export, so use `--output results/custom.json` to preserve the migration and regression fixtures.
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
the archived initial sample and 903 for the expanded sample. The production frontend joins MongoDB-backed API records by full ID and requests
Python-calculated comparisons in selection order. These exports remain migration
sources and regression fixtures; the browser does not load them or calculate cosmology.

## Data attribution

JADES HLSP products are provided under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Data DOI: [10.17909/8tdj-8n28](https://doi.org/10.17909/8tdj-8n28).
Credit the JADES collaboration, D'Eugenio et al. (DR3 spectroscopy), and
Eisenstein et al. (DR2 imaging), as linked above. These data are based on
NASA/ESA/CSA JWST observations obtained through MAST at STScI, operated by AURA
under NASA contract NAS 5-03127. Consult the source papers/archive for the full
acknowledgements when using the products in research.
