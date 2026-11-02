# Image-marker review

Reviewed the generated F200W map and all 15 native-pixel stamps on
2026-10-30 (America/New_York). The figure labels are NIRSpec IDs, all in the
`goods-s-deephst` tier. The rings come from `RA_NIRCam`, `Dec_NIRCam` transformed
through the cropped FITS WCS; positions were not adjusted to bright pixels.

Selected pair members checked visually:

- **16996:** ring overlaps the upper/central bright portion of an extended,
  roughly vertical source. The other bright object at the stamp's left edge is
  not selected. This is a useful check against a gross offset or wrong neighbor.
- **17160:** ring is centered on the compact source in the middle of its stamp.
- **17566:** ring overlaps the central faint compact source, distinct from the
  brighter objects above and below it.
- **19607:** ring is centered on a clear compact bright source.
- **19342:** faint source at the ring position; the brighter object to the
  upper left and bright structure at the bottom are separate objects.
- **21842:** a faint signal is visible around the catalog position, but this
  single F200W stamp is not strong independent evidence of source identity.
  Its identification relies on the catalog match and spectroscopy. No stronger
  visual claim is made for this target.

Additional checks: 19519 overlaps a bright compact source; 10008071 overlaps
the central light in an extended, elongated galaxy. The weaker high-redshift
targets are appropriately faint in this display. This is a qualitative alignment
review, not a measurement of astrometric accuracy or independent revalidation
of the spectroscopic identifications.

All 15 coordinates fall inside the cutout. The maximum difference between
parent-image coordinates minus the crop origin and the cropped-image coordinates
is about 6.1 × 10⁻⁸ pixel; the maximum sky/pixel/sky residual is about
7.3 × 10⁻¹¹ arcsec. These numerical checks accompany, rather than replace, the
visual review. See `verification.json` for reproducible numerical results.

## Frontend Prototype 1

Reviewed on 2026-11-02 (America/New_York). The clean PNG preserves all
2,000 × 2,000 native pixels and the finding chart's stretch, with its rows flipped
for browser display. The frontend uses the existing marker coordinates and
`y_display = height - 1 - y` in the same SVG as the image.

The desktop preview selects 17160, matching the compact source identified above,
with the full ID, z=1.850296, and about 16.6 billion comoving light-years in its
inspector. The mobile preview selects 10008071 (outside the three backend pairs),
with z=2.227103 and about 18.3 billion comoving light-years. Saved previews are
`frontend_desktop.jpg` and `frontend_mobile.jpg`.

Browser checks select all 15 galaxies using desktop clicks and mobile touch
coordinates, including the close neighboring sources. They verify that each
popup matches its JSON record, that only one selection is active, and that
close/Escape and keyboard selection work. Every marker's browser position relative
to the image is checked at 1440, 768, 390, and 320 pixel viewport widths.

## Three-filter color update

Reviewed on 2026-11-02 (America/New_York). The frontend now displays the static
F090W-blue / F200W-green / F444W-red composite on the original F200W grid.
Both additional DR2 mosaics have an integer-aligned pixel grid, with a maximum
residual of 2.73 × 10⁻⁹ pixel over 289 WCS control points including image edges.
They were cropped without interpolation. All 15 marker positions have coverage
in each band; the original F200W reference was used directly.

`color_alignment.jpg` compares unchanged marker centers on the original
grayscale and the new color image for 16996 and 17160 (lower sample edge),
10013682 (left), 10008071 (right), 21842 (upper), and 19342 (central). Extended
structure and compact source positions agree; differences in color and relative
brightness reflect the three filters and the display stretch. Faint objects
remain faint; the rings were not repositioned to brighter nearby sources.

The production build and all eight desktop/mobile browser checks pass, including
selection of all 15 galaxies and responsive overlay checks at 320–1440 pixel
viewport widths. The desktop inspection of 10008071 still shows about 18.3 billion
comoving light-years; the mobile inspection of 17160 still shows about 16.6 billion.
Saved previews are `frontend_color_desktop.jpg` and `frontend_color_mobile.jpg`.

SHA-256 comparisons confirm the existing sample, pair, marker, measurement, and
verification JSON files are byte-for-byte unchanged, as are the reference FITS,
grayscale PNG, data adapter, selection state, popup implementation, styles, and
distance calculations. Only the displayed map image and its caption/title changed
in the frontend. Full image provenance is in `goods_s_color.md`.
