# GOODS-S color image provenance

Static assigned-color composite from real JADES DR2 v2.0 NIRCam SCI data.
F090W maps to blue, F200W to green, and F444W to red. These infrared
bands are assigned visible colors; the rendering is not photometric data.

Reference: `data/goods_s_f200w_cutout.fits`; shape 2000 × 2000 pixels.
Reference SHA-256: `b8da2263320ed3e763fda10f851fcccea89434bc530a64f6650c775f9ef37eb7`.
The reference WCS, pixel scale, sky crop, and orientation are retained.
PNG coordinates are x_display = x, y_display = height - 1 - y.

Output: `results/goods_s_color.png`; SHA-256 `95fad1dc67ae864137672e022057d2df3da20e6393e2b21cd8e3138cacec330e`.
Common valid coverage: 96.68132500%; zero-filled/uncovered pixels remain black.

## Observations and registration

- F090W → blue: [MAST SCI mosaic](https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/hlsp_jades_jwst_nircam_goods-s-deep_f090w_v2.0_drz.fits).
  Registration: exact pixel crop; no interpolation; maximum residual from an integer grid
  over 289 control points (including image edges): 2.73032218132e-09 pixels.
  Native cached crop starts at parent (x, y) = [6902, 19813].
  Native crop SHA-256: `be3d606b651f3fb28ef21e127cdd2c9014c2ffdd2b2d07a833cb67f2bc2a9269`.
- F200W → green: [MAST SCI mosaic](https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/hlsp_jades_jwst_nircam_goods-s-deep_f200w_v2.0_drz.fits).
  Existing reference cutout used directly, without resampling.
- F444W → red: [MAST SCI mosaic](https://archive.stsci.edu/hlsps/jades/dr2/goods-s/images/hlsp_jades_jwst_nircam_goods-s-deep_f444w_v2.0_drz.fits).
  Registration: exact pixel crop; no interpolation; maximum residual from an integer grid
  over 289 control points (including image edges): 2.73032218132e-09 pixels.
  Native cached crop starts at parent (x, y) = [6902, 19813].
  Native crop SHA-256: `625bafd38d190268dc18c779806f176d7301347a1dc2420e70bf59d6351fa1d3`.

## Reproducible display settings

For each band, estimate median background and robust MAD noise from common
valid pixels. Subtract background + 0.5 × noise, clip negative display
values, and balance channels by their 99.7th-percentile signal.
Use Astropy's shared-intensity Lupton asinh mapping: stretch=0.08, Q=8.0.
This compresses bright cores while keeping faint source structure visible.

- F200W: background=0.000583186512813, noise=0.00300800497644, black=0.00208718900103, white=0.302634209394 MJy/sr.
- F090W: background=0.000515700317919, noise=0.00385606521741, black=0.00244373292662, white=0.131177350879 MJy/sr.
- F444W: background=0.000480281596538, noise=0.00203860015608, black=0.00149958167458, white=0.340154111385 MJy/sr.

Regenerate only when desired with `python -m starmap.color_image`.
Downloads are cached in data/cache/color. The website only loads the saved PNG;
it performs no image processing. Existing JSON, markers, selections, and
distance calculations are not written or changed by this command.
