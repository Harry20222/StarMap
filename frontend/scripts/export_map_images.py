"""Export display-only WebP sizes from the unchanged, aligned GOODS-S PNGs.

Run from the repository root with the existing project Python environment:
    python frontend/scripts/export_map_images.py
No crop, flip, rotation, stretch, or scientific data processing is applied.
"""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "frontend/src/assets"


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name in ("goods_s_color", "goods_s_f200w"):
        with Image.open(ROOT / "results" / f"{name}.png") as source:
            assert source.size == (2000, 2000), "Expected the existing square reference grid"
            for width in (640, 1280, 2000):
                image = source.convert("RGB")
                if width != source.width:
                    image = image.resize((width, width), Image.Resampling.LANCZOS)
                target = DESTINATION / f"{name}-{width}.webp"
                image.save(target, format="WEBP", quality=90, method=6)
                print(f"{target.name}: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
