"""Build a static JADES RGB image on the existing F200W reference pixel grid.

This optional, one-time image preparation command never writes catalog exports
or changes marker coordinates. Downloaded science crops are cached locally.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.visualization import make_lupton_rgb
from astropy.wcs import WCS
from PIL import Image
from scipy.ndimage import map_coordinates

from .data import sha256


FILTER_CHANNELS = {"F090W": "blue", "F200W": "green", "F444W": "red"}
MOSAIC_BASE = "https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/"


def source_url(filter_name):
    return MOSAIC_BASE + f"hlsp_jades_jwst_nircam_goods-s-deep_{filter_name.lower()}_v2.0_drz.fits"


def grid_points(shape, samples=17):
    y, x = np.meshgrid(np.linspace(0, shape[0] - 1, samples),
                       np.linspace(0, shape[1] - 1, samples), indexing="ij")
    return x, y


def fetch_native_crop(filter_name, reference_wcs, shape, cache_dir):
    destination = cache_dir / f"{filter_name.lower()}_native.fits"
    if destination.exists():
        return destination
    url = source_url(filter_name)
    print(f"{filter_name}: reading source WCS ...", flush=True)
    with fits.open(url, use_fsspec=True, lazy_load_hdus=True,
                   fsspec_kwargs={"block_size": 8 * 1024 * 1024,
                                  "cache_type": "readahead"}) as hdul:
        source = hdul["SCI"]
        source_wcs = WCS(source.header, fix=False).celestial
        tx, ty = grid_points(shape)
        sx, sy = source_wcs.world_to_pixel_values(*reference_wcs.pixel_to_world_values(tx, ty))
        # Include interpolation margin and determine the crop in sky coordinates,
        # rather than assuming the filters share mosaic dimensions or CRPIX.
        x0, x1 = int(np.floor(np.min(sx))) - 2, int(np.ceil(np.max(sx))) + 3
        y0, y1 = int(np.floor(np.min(sy))) - 2, int(np.ceil(np.max(sy))) + 3
        if not (0 <= x0 < x1 <= source.header["NAXIS1"]
                and 0 <= y0 < y1 <= source.header["NAXIS2"]):
            raise ValueError(f"{filter_name}: source mosaic does not cover the reference cutout")
        print(f"{filter_name}: fetching SCI[{y0}:{y1}, {x0}:{x1}] ...", flush=True)
        pixels = source.section[y0:y1, x0:x1].copy()
        header = source_wcs.slice((slice(y0, y1), slice(x0, x1))).to_header()
        header["FILTER"] = filter_name
        header["BUNIT"] = source.header["BUNIT"]
        header["PARENTX0"] = x0
        header["PARENTY0"] = y0
        header["HISTORY"] = url
        temporary = destination.with_suffix(".part.fits")
        fits.PrimaryHDU(pixels, header).writeto(temporary, overwrite=True)
        temporary.replace(destination)
    print(f"{filter_name}: cached native crop", flush=True)
    return destination


def align_to_reference(pixels, source_wcs, reference_wcs, shape):
    tx, ty = grid_points(shape)
    sx, sy = source_wcs.world_to_pixel_values(*reference_wcs.pixel_to_world_values(tx, ty))
    dx, dy = float(np.median(sx - tx)), float(np.median(sy - ty))
    ix, iy = int(round(dx)), int(round(dy))
    residual = float(np.max(np.hypot(sx - tx - ix, sy - ty - iy)))
    if residual < 1e-5:
        # An integer-aligned grid needs no resampling: retain the actual pixels.
        aligned = pixels[iy:iy + shape[0], ix:ix + shape[1]].copy()
        if ix < 0 or iy < 0 or aligned.shape != shape:
            raise ValueError("Cached source crop does not contain the complete reference grid")
        return aligned, "exact pixel crop; no interpolation", residual
    # Support other WCS grids without changing the reference or any marker.
    aligned = np.empty(shape, dtype=np.float32)
    for start in range(0, shape[0], 128):
        stop = min(start + 128, shape[0])
        y, x = np.mgrid[start:stop, 0:shape[1]]
        sx, sy = source_wcs.world_to_pixel_values(*reference_wcs.pixel_to_world_values(x, y))
        aligned[start:stop] = map_coordinates(pixels, [sy, sx], order=1,
                                              mode="constant", cval=np.nan, prefilter=False)
    return aligned, "bilinear WCS reprojection onto F200W reference", residual


def render_rgb(bands, *, stretch=0.08, q=8.0):
    """Display-only background subtraction, channel balance, and Lupton stretch.

    Zero-filled holes in the reference mosaic stay black. All measurements
    continue to use the original catalog, not these display intensities.
    """
    mask = np.logical_and.reduce([np.isfinite(a) & (a != 0) for a in bands.values()])
    scaled, settings = {}, {}
    for filter_name, pixels in bands.items():
        values = pixels[mask]
        background = float(np.median(values))
        sigma = float(1.4826 * np.median(np.abs(values - background)))
        black = background + 0.5 * sigma
        white = float(np.percentile(values, 99.7))
        scale = white - black
        if not scale > 0:
            raise ValueError(f"{filter_name}: no usable image contrast")
        scaled[filter_name] = np.where(mask, np.maximum(pixels - black, 0) / scale, 0)
        settings[filter_name] = {"background": background, "sigma": sigma,
                                 "black": black, "white": white}
    # Astropy masks zero-intensity pixels after evaluating a 0/0 expression.
    # Those pixels are intentionally black; suppress only this arithmetic warning.
    with np.errstate(invalid="ignore", divide="ignore"):
        rgb = make_lupton_rgb(scaled["F444W"], scaled["F200W"], scaled["F090W"],
                              minimum=0, stretch=stretch, Q=q, output_dtype=np.uint8)
    rgb[~mask] = 0
    return rgb, settings, float(np.mean(mask))


def build_color_image(reference_path, output_path, cache_dir, *, stretch=0.08, q=8.0):
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with fits.open(reference_path) as hdul:
        reference = hdul[0].data.copy()
        reference_wcs = WCS(hdul[0].header, fix=False).celestial
        reference_unit = hdul[0].header["BUNIT"]
    shape = reference.shape
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {name: executor.submit(fetch_native_crop, name, reference_wcs, shape, cache_dir)
                   for name in ("F090W", "F444W")}
        crops = {name: future.result() for name, future in futures.items()}
    bands = {"F200W": reference}
    checks = {}
    for name, path in crops.items():
        with fits.open(path) as hdul:
            if hdul[0].header["BUNIT"] != reference_unit:
                raise ValueError(f"{name}: incompatible surface-brightness units")
            aligned, method, residual = align_to_reference(hdul[0].data,
                WCS(hdul[0].header, fix=False).celestial, reference_wcs, shape)
            bands[name] = aligned
            checks[name] = {"method": method, "residual": residual,
                            "native_sha256": sha256(path),
                            "parent_crop": [hdul[0].header["PARENTX0"], hdul[0].header["PARENTY0"]]}
    rgb, settings, coverage = render_rgb(bands, stretch=stretch, q=q)
    # Preserve the exact same browser orientation as goods_s_f200w.png.
    Image.fromarray(np.flipud(rgb)).save(output_path)
    report = ["# GOODS-S color image provenance", "",
        "Static assigned-color composite from real JADES DR2 v2.0 NIRCam SCI data.",
        "F090W maps to blue, F200W to green, and F444W to red. These infrared",
        "bands are assigned visible colors; the rendering is not photometric data.", "",
        f"Reference: `{reference_path.as_posix()}`; shape {shape[1]} × {shape[0]} pixels.",
        f"Reference SHA-256: `{sha256(reference_path)}`.",
        "The reference WCS, pixel scale, sky crop, and orientation are retained.",
        "PNG coordinates are x_display = x, y_display = height - 1 - y.", "",
        f"Output: `{output_path.as_posix()}`; SHA-256 `{sha256(output_path)}`.",
        f"Common valid coverage: {coverage:.8%}; zero-filled/uncovered pixels remain black.", "",
        "## Observations and registration", ""]
    for name in FILTER_CHANNELS:
        report.append(f"- {name} → {FILTER_CHANNELS[name]}: [MAST SCI mosaic]({source_url(name)}).")
        if name in checks:
            check = checks[name]
            report.extend([f"  Registration: {check['method']}; maximum residual from an integer grid",
                f"  over 289 control points (including image edges): {check['residual']:.12g} pixels.",
                f"  Native cached crop starts at parent (x, y) = {check['parent_crop']}.",
                f"  Native crop SHA-256: `{check['native_sha256']}`."])
        else:
            report.append("  Existing reference cutout used directly, without resampling.")
    report.extend(["", "## Reproducible display settings", "",
        "For each band, estimate median background and robust MAD noise from common",
        "valid pixels. Subtract background + 0.5 × noise, clip negative display",
        "values, and balance channels by their 99.7th-percentile signal.",
        f"Use Astropy's shared-intensity Lupton asinh mapping: stretch={stretch}, Q={q}.",
        "This compresses bright cores while keeping faint source structure visible.", ""])
    for name, setting in settings.items():
        report.append(f"- {name}: background={setting['background']:.12g}, noise={setting['sigma']:.12g}, "
                      f"black={setting['black']:.12g}, white={setting['white']:.12g} {reference_unit}.")
    report.extend(["", "Regenerate only when desired with `python -m starmap.color_image`.",
        "Downloads are cached in data/cache/color. The website only loads the saved PNG;",
        "it performs no image processing. Existing JSON, markers, selections, and",
        "distance calculations are not written or changed by this command.", ""])
    output_path.with_suffix(".md").write_text("\n".join(report), encoding="utf-8")
    print(f"Saved {output_path} ({shape[1]} × {shape[0]})", flush=True)
    for name, check in checks.items():
        print(f"{name}: {check['method']}; grid residual {check['residual']:.3g} pixels", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=Path("data/goods_s_f200w_cutout.fits"))
    parser.add_argument("--output", type=Path, default=Path("results/goods_s_color.png"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache/color"))
    parser.add_argument("--stretch", type=float, default=0.08)
    parser.add_argument("--q", type=float, default=8.0)
    args = parser.parse_args(argv)
    if args.stretch <= 0 or args.q <= 0:
        parser.error("stretch and q must be positive")
    build_color_image(args.reference, args.output, args.cache_dir, stretch=args.stretch, q=args.q)


if __name__ == "__main__":
    main()
