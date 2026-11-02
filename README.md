# StarMap: JADES galaxy distances

A Python backend and React/TypeScript field explorer for learning to match JWST
images to galaxy catalogs and measure distances with Astropy's **Planck18** cosmology. The bundled
sample contains **15 real JADES galaxies with flag-A spectroscopic redshifts** in
a single GOODS-S NIRCam F200W cutout. Three fixed pairs produce terminal output
and frontend-friendly JSON without network access.

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

Frontend Prototype 1 lets you select any of the 15 quality-A galaxies on the
GOODS-S image and inspect its estimated comoving distance, sky coordinates,
redshift, quality, and published uncertainty status. Comparing two galaxies in
the interface remains a later milestone.

## Frontend: open the field explorer

The frontend is in `frontend/` and uses React, TypeScript, CSS, and Vite. It
imports the backend JSON files and clean PNG directly; **no Python API server
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

Thin green rings identify selectable quality-A galaxies; the legend count comes
from the joined JSON data. A selected galaxy gets a distinct amber outline.
Click another ring to update the inspector, or dismiss with its close button or
Escape. Tab and Enter/Space also select markers. On small screens, the inspector
appears below the image and scrolls into view without covering the other rings.

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

See `frontend/README.md` for component structure, data flow, and browser tests.

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
saves `results/measurements.json`. Data paths are resolved relative to the script,
so the editor's working directory does not matter. Keep the rest of the project
files alongside the launcher; it uses the existing modules and bundled data.

```powershell
# Override the three default pairs with one pair; --pair can be repeated.
.\my_venv\Scripts\python.exe -m starmap --pair goods-s-deephst:17160 goods-s-deephst:19607 --output results\custom.json

# Rebuild finding charts and perform independent numerical/WCS checks.
.\my_venv\Scripts\python.exe -m starmap.imaging
.\my_venv\Scripts\python.exe -m starmap.verify

# Optional: retrieve/cache original source files and rebuild the sample.
.\my_venv\Scripts\python.exe -m starmap.prepare
```

Edit `data/pairs.json` to change the default pair list. IDs use `TIER:NIRSpec_ID`;
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
- Selection: `TIER == goods-s-deephst`, flag A, positive finite `z_Spec`, no
  `DR_flag`, valid NIRCam match and coordinates. Deduplicate by NIRCam ID, choose
  the 15 nearest to the fixed center, and sort by NIRSpec ID. The recipe is in
  `starmap/prepare.py`; source row indices and all 15 full records are saved.

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

## Three reproducible pairs

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

`results/galaxy_map.png` labels all 15 positions. `results/alignment_stamps.png`
shows 3-arcsec stamps with open rings, preserving source visibility. Visual
inspection is recorded in `results/alignment_review.md`; some targets are faint
in this single filter. Dark masked regions in the mosaic are not sky structures.
`results/goods_s_f200w.png` is the original clean, unannotated 2,000 × 2,000
grayscale reference, with pixel rows flipped for top-left browser coordinates.
The frontend now displays the static `results/goods_s_color.png`: real JADES DR2
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
the raw FITS image dimensions. The UI uses the clean pixel-only PNG instead.

## Data attribution

JADES HLSP products are provided under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Data DOI: [10.17909/8tdj-8n28](https://doi.org/10.17909/8tdj-8n28).
Credit the JADES collaboration, D'Eugenio et al. (DR3 spectroscopy), and
Eisenstein et al. (DR2 imaging), as linked above. These data are based on
NASA/ESA/CSA JWST observations obtained through MAST at STScI, operated by AURA
under NASA contract NAS 5-03127. Consult the source papers/archive for the full
acknowledgements when using the products in research.
