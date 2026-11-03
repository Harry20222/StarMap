"""WCS marker projection and static scientific finding charts."""

import argparse
from math import ceil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize, PercentileInterval
from astropy.wcs import WCS

from .data import load_sample, write_json


def project_markers(galaxies, wcs, shape):
    rows = []
    for g in galaxies:
        if not g.has_coordinates:
            continue
        sky = SkyCoord(g.ra_deg, g.dec_deg, unit="deg")
        x, y = (float(p) for p in wcs.world_to_pixel(sky))
        residual = float(sky.separation(wcs.pixel_to_world(x, y)).arcsec)
        rows.append({"galaxy_id": g.galaxy_id, "x": x, "y": y,
                     "inside_image": bool(-0.5 <= x < shape[1] - 0.5 and -0.5 <= y < shape[0] - 0.5),
                     "roundtrip_residual_arcsec": residual})
    return rows


def norm_for(pixels):
    finite = pixels[np.isfinite(pixels)]
    return ImageNormalize(finite, interval=PercentileInterval(99.5), stretch=AsinhStretch(0.04))


def export_clean_image(pixels, destination: Path):
    """Export native pixels without axes or markers, flipped for browser display.

    Use the same grayscale/asinh stretch as the reference finding chart.
    FITS pixel center (x, y) is PNG pixel center (x, height - 1 - y).
    """
    rgba = plt.get_cmap("gray")(norm_for(pixels)(pixels))
    plt.imsave(destination, rgba, origin="lower")


def make_charts(sample_path: Path, output_dir: Path):
    document, galaxies = load_sample(sample_path)
    image = sample_path.parent / document["dataset"]["image_file"]
    with fits.open(image) as hdul:
        pixels, wcs = hdul[0].data.copy(), WCS(hdul[0].header, fix=False).celestial
    markers = project_markers(galaxies, wcs, pixels.shape)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_clean_image(pixels, output_dir / "goods_s_f200w.png")
    write_json(output_dir / "markers.json", {
        "image": str(image), "shape_yx": list(pixels.shape),
        "display_image": "goods_s_f200w.png",
        "pixel_origin": 0, "display_origin": "lower", "markers": markers,
        "frontend_note": "For a top-left-origin image, y_display = height - 1 - y; scale both axes when resizing.",
    })
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": wcs})
    ax.imshow(pixels, origin="lower", cmap="gray", norm=norm_for(pixels))
    for g, marker in zip(galaxies, markers):
        x, y = marker["x"], marker["y"]
        ax.scatter(x, y, s=120, facecolors="none", edgecolors="#48e0ff", linewidths=0.9)
        ax.annotate(str(g.nirspec_id), (x, y), xytext=(8, 7), textcoords="offset points",
                    color="#48e0ff", fontsize=8)
    ax.set_title(f"JADES GOODS-S | NIRCam F200W | DR2 v2.0\n{len(galaxies)} DR3 flag-A galaxies; labels are NIRSpec IDs (tiers in sample.json)")
    ax.set_xlabel("Right ascension (ICRS)")
    ax.set_ylabel("Declination (ICRS)")
    fig.tight_layout()
    fig.savefig(output_dir / "galaxy_map.png", dpi=160)
    plt.close(fig)
    # Inspect every sample member in 3-arcsec native-pixel stamps.
    rows = max(1, ceil(len(galaxies) / 5))
    fig, axes = plt.subplots(rows, 5, figsize=(15, rows * 3), squeeze=False)
    for ax, g, marker in zip(axes.flat, galaxies, markers):
        x, y = marker["x"], marker["y"]
        xi, yi = int(round(x)), int(round(y))
        x0, x1 = max(0, xi - 50), min(pixels.shape[1], xi + 51)
        y0, y1 = max(0, yi - 50), min(pixels.shape[0], yi + 51)
        stamp = pixels[y0:y1, x0:x1]
        ax.imshow(stamp, origin="lower", cmap="gray", norm=norm_for(stamp),
                  extent=(x0 - 0.5, x1 - 0.5, y0 - 0.5, y1 - 0.5))
        ax.scatter(x, y, s=180, facecolors="none", edgecolors="#48e0ff", linewidths=0.9)
        ax.plot([x - 13, x - 7, np.nan, x + 7, x + 13], [y] * 5, color="#48e0ff", lw=0.8)
        ax.set_title(f"{g.nirspec_id} | z={g.redshift:.5f} | A", fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in list(axes.flat)[len(galaxies):]:
        ax.set_visible(False)
    fig.suptitle("WCS alignment check | 3 arcsec stamps | open rings at catalog positions", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_dir / "alignment_stamps.png", dpi=140)
    plt.close(fig)
    return markers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/sample.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args(argv)
    markers = make_charts(args.sample, args.output_dir)
    print(f"Projected {len(markers)} markers; max WCS roundtrip residual "
          f"{max(m['roundtrip_residual_arcsec'] for m in markers):.3g} arcsec")


if __name__ == "__main__":
    main()
