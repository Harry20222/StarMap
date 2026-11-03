import color640 from "../assets/goods_s_color-640.webp?url";
import color1280 from "../assets/goods_s_color-1280.webp?url";
import color2000 from "../assets/goods_s_color-2000.webp?url";
import grayscale640 from "../assets/goods_s_f200w-640.webp?url";
import grayscale1280 from "../assets/goods_s_f200w-1280.webp?url";
import grayscale2000 from "../assets/goods_s_f200w-2000.webp?url";

const sources = {
  color: [color640, color1280, color2000],
  grayscale: [grayscale640, grayscale1280, grayscale2000],
};
const widths = [640, 1280, 2000];

export function MapImage({
  mode,
  displayWidth,
  width,
  height,
  onError,
}: {
  mode: "color" | "grayscale";
  displayWidth: number;
  width: number;
  height: number;
  onError: () => void;
}) {
  // Wait for the actual SVG width so a phone never requests a desktop fallback
  // first. Importing an asset URL does not fetch the image; only this href does.
  if (displayWidth <= 0) return null;
  const required = displayWidth * (window.devicePixelRatio || 1);
  const index = widths.findIndex((size) => size >= required);
  const variant = index === -1 ? widths.length - 1 : index;
  return (
    <image
      href={sources[mode][variant]}
      x={-0.5}
      y={-0.5}
      width={width}
      height={height}
      data-image-width={widths[variant]}
      onError={onError}
      aria-hidden="true"
    />
  );
}
