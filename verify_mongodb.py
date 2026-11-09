"""Read-only verification of imported records and all 903 API pair results."""

import json
from math import isclose
import sys
from urllib.parse import urlencode

from pymongo.errors import PyMongoError

from app import dispatch
from starmap.database import close_client, get_database
from starmap.migration import ROOT, prepare_import, verify_import


def main():
    try:
        prepared = prepare_import()
        database = get_database()
        counts = verify_import(database, prepared)
        catalog = dispatch("/api/maps/goods-s/galaxies", "")
        if len(catalog["galaxies"]) != 43 or len(catalog["markers"]) != 43:
            raise ValueError("Incomplete API catalog")
        exported = json.loads((ROOT / "results/measurements.json").read_text())
        for index, expected in enumerate(exported["pairs"], 1):
            query = urlencode({"a": expected["galaxy_a_id"], "b": expected["galaxy_b_id"]})
            actual = dispatch("/api/maps/goods-s/compare", query)
            for key in ("angular_separation", "distance_from_us_a", "distance_from_us_b", "estimated_3d_separation"):
                if actual[key]["unit"] != expected[key]["unit"] or not isclose(
                    actual[key]["value"], expected[key]["value"], rel_tol=1e-10, abs_tol=1e-12,
                ):
                    raise ValueError("API regression mismatch")
            if index % 100 == 0:
                print(f"Verified {index}/903 comparisons.", flush=True)
        print(json.dumps({"verified": counts, "api_comparisons": len(exported["pairs"]),
                          "relative_tolerance": 1e-10, "absolute_tolerance": 1e-12}))
    except (PyMongoError, ValueError, OSError, KeyError, TypeError) as error:
        print(f"Verification failed ({type(error).__name__}). Check the imported data and server settings.", file=sys.stderr)
        return 1
    finally:
        close_client()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
