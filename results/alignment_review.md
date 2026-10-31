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
