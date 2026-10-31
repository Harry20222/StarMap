from dataclasses import replace
import json
import math

import astropy.units as u
from astropy.cosmology import Planck18
import pytest

from starmap import Galaxy, measure_pair
from starmap.calculations import comoving_distance_ly
from starmap.verify import independent_pair


def galaxy(**kwargs):
    return replace(Galaxy("test", 53.16, -27.77, 2.0, "A"), **kwargs)


def test_swap_preserves_separation_and_swaps_radial_distances():
    a, b = galaxy(), galaxy(galaxy_id="other", ra_deg=53.17, redshift=2.1)
    ab, ba = measure_pair(a, b), measure_pair(b, a)
    for key in ("angular_separation", "estimated_3d_separation"):
        assert ab[key]["value"] == pytest.approx(ba[key]["value"], rel=1e-12)
    assert ab["distance_from_us_a"] == ba["distance_from_us_b"]


def test_self_separations_are_exactly_zero():
    result = measure_pair(galaxy(), galaxy())
    assert result["angular_separation"]["value"] == 0
    assert result["estimated_3d_separation"]["value"] == 0


def test_equal_redshift_has_nonzero_transverse_separation():
    a, b = galaxy(ra_deg=0, dec_deg=0), galaxy(ra_deg=60, dec_deg=0)
    result = measure_pair(a, b)
    assert result["angular_separation"]["value"] == pytest.approx(60)
    # For a 60-degree chord on a sphere of radius r, the separation is r.
    assert result["estimated_3d_separation"]["value"] == pytest.approx(comoving_distance_ly(a))


def test_same_direction_is_radial_difference():
    a, b = galaxy(), galaxy(redshift=3)
    result = measure_pair(a, b)
    expected = abs(comoving_distance_ly(a) - comoving_distance_ly(b))
    assert result["estimated_3d_separation"]["value"] == pytest.approx(expected)


def test_right_angle_geometry():
    a, b = galaxy(ra_deg=0, dec_deg=0), galaxy(ra_deg=90, dec_deg=0, redshift=3)
    result = measure_pair(a, b)
    expected = math.hypot(comoving_distance_ly(a), comoving_distance_ly(b))
    assert result["estimated_3d_separation"]["value"] == pytest.approx(expected)


def test_wraparound_and_poles():
    a, b = galaxy(ra_deg=359.9, dec_deg=0), galaxy(ra_deg=0.1, dec_deg=0)
    assert measure_pair(a, b)["angular_separation"]["value"] == pytest.approx(0.2)
    assert measure_pair(galaxy(dec_deg=90), galaxy(dec_deg=-90))["angular_separation"]["value"] == pytest.approx(180)


@pytest.mark.parametrize("field,value", [
    ("ra_deg", -1), ("ra_deg", 360), ("dec_deg", -91), ("dec_deg", 91),
    ("redshift", -1), ("redshift", float("nan")), ("ra_deg", float("inf")),
    ("redshift", "2"), ("redshift", True), ("redshift_uncertainty", -0.1),
    ("redshift_quality", ["A"]),
])
def test_invalid_input_is_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        galaxy(**{field: value})


@pytest.mark.parametrize("missing", ["ra_deg", "dec_deg", "redshift"])
def test_missing_data_is_explicit_and_json_safe(missing):
    result = measure_pair(galaxy(**{missing: None}), galaxy())
    assert result["status"] == "unknown"
    assert result["estimated_3d_separation"]["value"] is None
    if missing == "redshift":
        assert result["angular_separation"]["value"] == 0
        assert result["distance_from_us_a"]["value"] is None
    else:
        assert result["angular_separation"]["value"] is None
        assert result["distance_from_us_a"]["value"] is not None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("flag", ["C", "D", "E", None, "unrecognized"])
def test_low_or_unknown_quality_does_not_become_distance(flag):
    assert comoving_distance_ly(galaxy(redshift_quality=flag)) is None


def test_quality_is_separate_from_numerical_uncertainty():
    g = galaxy()
    assert g.metadata()["redshift_uncertainty"] is None
    assert g.metadata()["redshift_quality"] == "A"
    assert comoving_distance_ly(galaxy(redshift_quality="B")) is not None
    assert galaxy(redshift_uncertainty=0.001).metadata()["redshift_uncertainty_status"] == "published"


def test_units_and_independent_integral_cartesian_crosscheck():
    a, b = galaxy(), galaxy(ra_deg=53.2, dec_deg=-27.8, redshift=3.7)
    measured, independent = measure_pair(a, b), independent_pair(a, b)
    assert measured["distance_from_us_a"]["unit"] == "ly"
    assert comoving_distance_ly(a) == pytest.approx(Planck18.comoving_distance(2).to_value(u.lyr))
    assert measured["angular_separation"]["value"] == pytest.approx(independent["angular_separation_deg"], rel=1e-10)
    assert measured["estimated_3d_separation"]["value"] == pytest.approx(independent["estimated_3d_separation_ly"], rel=1e-10)


def test_zero_redshift_is_valid_distance_zero():
    assert comoving_distance_ly(galaxy(redshift=0)) == 0
