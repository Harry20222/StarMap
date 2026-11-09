"""Import the existing GOODS-S sample into the configured MongoDB database."""

import argparse
import json
import sys

from pymongo.errors import PyMongoError

from starmap.database import close_client, get_database
from starmap.migration import import_data, prepare_import


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate local sources without accessing MongoDB.")
    args = parser.parse_args()
    try:
        prepared = prepare_import()
        if args.validate_only:
            print("Validated GOODS-S: 1 map, 43 quality-A galaxies, 43 WCS-aligned markers.")
        else:
            print(json.dumps(import_data(get_database(), prepared), indent=2))
    except (PyMongoError, ValueError, OSError, KeyError, TypeError) as error:
        # URI, hostnames, credentials, and driver diagnostics stay out of output.
        print(f"Import failed ({type(error).__name__}). Check source validation, settings, network access and write permissions.", file=sys.stderr)
        return 1
    finally:
        close_client()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
