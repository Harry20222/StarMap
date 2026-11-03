"""Frontend-friendly output schema and human-readable terminal formatting."""

import astropy
from itertools import combinations
import astropy.units as u
from astropy.cosmology import Planck18

from .calculations import comoving_distance_ly, measure_pair
from .selection import select_pairs


def build_results(sample_document, galaxies, pairs=None):
    selected_pairs = (combinations(galaxies, 2) if pairs is None
                      else select_pairs(galaxies, pairs))
    return {
        "schema_version": "1.2",
        "cosmology": {
            "name": "Planck18", "class": type(Planck18).__name__,
            "H0": {"value": Planck18.H0.value, "unit": "km / (Mpc s)"},
            "Om0": Planck18.Om0, "Ode0": Planck18.Ode0,
            "Ob0": Planck18.Ob0, "Ok0": Planck18.Ok0,
            "Tcmb0_K": Planck18.Tcmb0.to_value(u.K), "Neff": Planck18.Neff,
            "m_nu_eV": Planck18.m_nu.to_value(u.eV).tolist(),
            "astropy_version": astropy.__version__,
        },
        "distance_convention": "comoving; scale factor a0 = 1; light-years (ly)",
        "interpretation": (
            "3D separations are model-based estimates from redshift-space positions, "
            "not light-travel times or separations at either emission epoch. "
            "Peculiar velocities, redshift errors, and cosmological parameter errors "
            "are not propagated. Decimal digits do not indicate physical accuracy."
        ),
        "reliable_redshift_flags": ["A", "B"],
        "dataset": sample_document["dataset"],
        "galaxies": [
            {**g.metadata(), "distance_from_us": {
                "value": comoving_distance_ly(g), "unit": "ly", "convention": "comoving",
            }}
            for g in galaxies
        ],
        "pairs": [measure_pair(a, b) for a, b in selected_pairs],
    }


def terminal_summary(results):
    lines = ["Astropy Planck18 | distances are comoving light-years (ly)",
             "3D separations are model-based estimates; uncertainties are not propagated."]
    for pair in results["pairs"]:
        lines.append(f"\n{pair['galaxy_a_id']}  <->  {pair['galaxy_b_id']}")
        for key, label in (
            ("angular_separation", "Angular separation"),
            ("distance_from_us_a", "Comoving distance from us to A"),
            ("distance_from_us_b", "Comoving distance from us to B"),
            ("estimated_3d_separation", "Estimated comoving 3D separation"),
        ):
            item = pair[key]
            value = "unknown" if item["value"] is None else f"{item['value']:.10g}"
            lines.append(f"  {label}: {value} {item['unit']}")
        lines.extend(f"  {reason}" for reason in pair["unknown_reasons"])
    return "\n".join(lines)
