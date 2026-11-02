"""Run this file to open the React field explorer in your browser."""

from pathlib import Path
import shutil
import subprocess


def main():
    frontend = Path(__file__).resolve().parent / "frontend"
    node = shutil.which("node")
    vite = frontend / "node_modules" / "vite" / "bin" / "vite.js"
    if node is None:
        raise SystemExit("Install Node.js 22.12+ (or 20.19+) to run the frontend.")
    if not vite.is_file():
        raise SystemExit("Install the frontend dependencies first: run npm ci inside the frontend folder.")
    print("Opening the StarMap field explorer. Stop this script to stop its preview server.", flush=True)
    try:
        result = subprocess.run([node, str(vite), "--host", "127.0.0.1", "--open"], cwd=frontend)
    except KeyboardInterrupt:
        return
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
