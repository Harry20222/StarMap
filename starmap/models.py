"""Galaxy records and explicit input validation; no I/O."""

from dataclasses import asdict, dataclass
from math import isfinite


QUALITY_MEANINGS = {
    "A": "Highly robust: emission lines with S/N > 5 in R~1000 grating spectra.",
    "B": "Highly robust: emission lines with S/N > 5 in Prism/Clear spectra.",
    "C": "Secure: visually identified spectral breaks and/or low-S/N emission lines.",
    "D": "Tentative redshift.",
    "E": "No redshift.",
}
RELIABLE_FLAGS = frozenset({"A", "B"})


@dataclass(frozen=True)
class Galaxy:
    galaxy_id: str
    ra_deg: float | None
    dec_deg: float | None
    redshift: float | None
    redshift_quality: str | None
    redshift_uncertainty: float | None = None
    nirspec_id: int | None = None
    tier: str | None = None
    nircam_id: int | None = None
    catalog_row_index: int | None = None

    def __post_init__(self):
        if not isinstance(self.galaxy_id, str) or not self.galaxy_id.strip():
            raise ValueError("galaxy_id must be a nonempty string")
        if self.redshift_quality is not None and not isinstance(self.redshift_quality, str):
            raise ValueError("redshift_quality must be a string or None")
        for name in ("ra_deg", "dec_deg", "redshift", "redshift_uncertainty"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
            ):
                raise ValueError(f"{name} must be a finite number or None")
        if self.ra_deg is not None and not 0 <= self.ra_deg < 360:
            raise ValueError("ra_deg must be in [0, 360)")
        if self.dec_deg is not None and not -90 <= self.dec_deg <= 90:
            raise ValueError("dec_deg must be in [-90, 90]")
        if self.redshift is not None and self.redshift < 0:
            raise ValueError("redshift must be nonnegative or None")
        if self.redshift_uncertainty is not None and self.redshift_uncertainty < 0:
            raise ValueError("redshift_uncertainty must be nonnegative or None")

    @property
    def has_coordinates(self):
        return self.ra_deg is not None and self.dec_deg is not None

    @property
    def has_reliable_redshift(self):
        return self.redshift is not None and self.redshift_quality in RELIABLE_FLAGS

    def metadata(self):
        result = asdict(self)
        result["coordinate_frame"] = "ICRS"
        result["redshift_quality_meaning"] = QUALITY_MEANINGS.get(
            self.redshift_quality, "Unknown quality flag; distance unavailable."
        )
        result["redshift_uncertainty_status"] = (
            "not_published_in_selected_catalog"
            if self.redshift_uncertainty is None else "published"
        )
        result["distance_status"] = (
            "available" if self.has_reliable_redshift else "unknown"
        )
        return result
