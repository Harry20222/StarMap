"""Run with python -m starmap, or the installed starmap command."""

import argparse
import json
from pathlib import Path

from .data import load_sample, write_json
from .output import build_results, terminal_summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="JADES / Planck18 galaxy distances")
    parser.add_argument("--sample", type=Path, default=Path("data/sample.json"))
    parser.add_argument("--pairs", type=Path, default=Path("data/pairs.json"))
    parser.add_argument("--output", type=Path, default=Path("results/measurements.json"))
    parser.add_argument("--pair", nargs=2, action="append", metavar=("ID_A", "ID_B"),
                        help="Explicit pair; repeat to override the pairs file")
    args = parser.parse_args(argv)
    try:
        document, galaxies = load_sample(args.sample)
        pairs = args.pair or json.loads(args.pairs.read_text(encoding="utf-8"))["pairs"]
        results = build_results(document, galaxies, pairs)
        write_json(args.output, results)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"starmap: {exc}\n")
    print(terminal_summary(results))
    print(f"\nJSON: {args.output}")


if __name__ == "__main__":
    main()
