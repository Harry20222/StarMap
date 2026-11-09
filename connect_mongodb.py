"""Check the online MongoDB connection without inserting or changing data.

"""

import sys

from pymongo.errors import PyMongoError
from starmap.database import close_client, get_database


def main() -> int:
    try:
        database = get_database()
        database.command("ping")
    except (PyMongoError, ValueError) as error:
        # Driver messages can contain connection details. Keep credentials out
        # of terminal output while identifying the class of failure.
        print(f"MongoDB connection failed ({type(error).__name__}).", file=sys.stderr)
        print(
            "Check the URI, database name, database-user credentials, and "
            "Atlas network access for this computer.",
            file=sys.stderr,
        )
        return 1
    finally:
        close_client()

    print("MongoDB connection successful for the configured database.")
    print("Server ping passed. Collection access and data imports are separate steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
