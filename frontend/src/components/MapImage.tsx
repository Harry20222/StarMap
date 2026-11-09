import type { ImageAssets } from "../data/galaxies";
import { imageSources } from "../data/imageAssets";

export function MapImage({
  mode,
  assets,
  displayWidth,
  width,
  height,
  onError,
}: {
  mode: "color" | "grayscale";
  assets: ImageAssets;
  displayWidth: number;
  width: number;
  height: number;
  onError: () => void;
}) {
  // Wait for the actual SVG width so a phone never requests a desktop fallback
  // first. Importing an asset URL does not fetch the image; only this href does.
  if (displayWidth <= 0) return null;
  const required = displayWidth * (window.devicePixelRatio || 1);
  const variants = assets[mode];
  const variant = variants.find((v) => v.width >= required) ?? variants[variants.length - 1];
  const source = imageSources[variant.asset];
  if (!source) throw new Error("The map image asset is not available in this build.");
  return (
    <image
      href={source}
      x={-0.5}
      y={-0.5}
      width={width}
      height={height}
      data-image-width={variant.width}
      onError={onError}
      aria-hidden="true"
    />
  );
}
