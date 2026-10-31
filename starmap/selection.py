"""Select explicit pairs by unambiguous tier-qualified galaxy IDs."""

from .models import Galaxy


def select_pairs(galaxies: list[Galaxy], pairs: list[list[str]]):
    by_id = {g.galaxy_id: g for g in galaxies}
    if len(by_id) != len(galaxies):
        raise ValueError("Duplicate galaxy IDs")
    result = []
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError("Each pair must contain exactly two galaxy IDs")
        try:
            result.append((by_id[pair[0]], by_id[pair[1]]))
        except KeyError as exc:
            raise ValueError(f"Unknown galaxy ID: {exc.args[0]}") from exc
    return result
