"""Pure calculation functions using one fixed, spatially flat cosmology."""

from math import hypot, sin

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.cosmology import Planck18

from .models import Galaxy


def comoving_distance_ly(galaxy: Galaxy) -> float | None:
    if not galaxy.has_reliable_redshift:
        return None
    return float(Planck18.comoving_distance(galaxy.redshift).to_value(u.lyr))


def angular_separation_deg(a: Galaxy, b: Galaxy) -> float | None:
    if not (a.has_coordinates and b.has_coordinates):
        return None
    ca = SkyCoord(a.ra_deg, a.dec_deg, unit="deg", frame="icrs")
    cb = SkyCoord(b.ra_deg, b.dec_deg, unit="deg", frame="icrs")
    return float(ca.separation(cb).deg)


def measure_pair(a: Galaxy, b: Galaxy) -> dict:
    """Return four measurements; missing data produce JSON-safe nulls.

    The half-angle form of the law of cosines avoids subtracting two nearly
    equal squared distances for objects at almost the same position.
    """
    theta = angular_separation_deg(a, b)
    da, db = comoving_distance_ly(a), comoving_distance_ly(b)
    separation = None
    if theta is not None and da is not None and db is not None:
        half_angle = (theta * u.deg).to_value(u.rad) / 2
        separation = hypot(da - db, 2 * (da * db) ** 0.5 * sin(half_angle))
    reasons = []
    for g in (a, b):
        if not g.has_coordinates:
            reasons.append(f"{g.galaxy_id}: missing coordinates")
        if not g.has_reliable_redshift:
            reasons.append(f"{g.galaxy_id}: missing redshift or quality outside A/B")
    return {
        "galaxy_a_id": a.galaxy_id,
        "galaxy_b_id": b.galaxy_id,
        "status": "available" if separation is not None else "unknown",
        "unknown_reasons": reasons,
        "angular_separation": {"value": theta, "unit": "deg"},
        "distance_from_us_a": {"value": da, "unit": "ly", "convention": "comoving"},
        "distance_from_us_b": {"value": db, "unit": "ly", "convention": "comoving"},
        "estimated_3d_separation": {
            "value": separation, "unit": "ly", "convention": "comoving",
            "method": "flat-space law of cosines using both sky directions and radial distances",
            "uncertainty": None,
            "uncertainty_status": "not_propagated",
        },
    }
