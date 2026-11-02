"""Run this file to print the three default galaxy pairs and export their JSON."""

from pathlib import Path
import sys

from starmap.cli import main


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    main([
        "--sample", str(project_dir / "data" / "sample.json"),
        "--pairs", str(project_dir / "data" / "pairs.json"),
        "--output", str(project_dir / "results" / "measurements.json"),
        *sys.argv[1:],
    ])
