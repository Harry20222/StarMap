import { useEffect, useRef, useState, type MouseEvent } from "react";
import colorImage from "../../../results/goods_s_color.png?url";
import grayscaleImage from "../../../results/goods_s_f200w.png?url";
import type { GalaxyField, SelectableGalaxy } from "../data/galaxies";

type GalaxyMapProps = {
  field: GalaxyField;
  selectedId: string | null;
  onSelect: (galaxy: SelectableGalaxy) => void;
};

export function GalaxyMap({ field, selectedId, onSelect }: GalaxyMapProps) {
  const [imageMode, setImageMode] = useState<"color" | "grayscale">("color");
  const imageCaption = imageMode === "color"
    ? `${field.dataset.field} · F090W (blue) + F200W (green) + F444W (red) color image (${field.dataset.image_release}) · galaxy catalog (${field.dataset.catalog_release}).`
    : `${field.dataset.field} · F200W black-and-white image (${field.dataset.image_release}) · galaxy catalog (${field.dataset.catalog_release}).`;
  const frame = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [displayWidth, setDisplayWidth] = useState(800);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    if (!frame.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setDisplayWidth(entry.contentRect.width),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);

  const scale = Math.max(displayWidth / field.width, 0.001);
  const ringRadius = Math.max(17, 6 / scale);
  const hitRadius = Math.max(ringRadius + 9, 22 / scale);

  function selectNearest(
    event: MouseEvent<SVGGElement>,
    fallback: SelectableGalaxy,
  ) {
    if (event.detail === 0 || !svgRef.current) {
      onSelect(fallback);
      return;
    }
    const matrix = svgRef.current.getScreenCTM();
    if (!matrix) {
      onSelect(fallback);
      return;
    }
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(
      matrix.inverse(),
    );
    // Touch targets may overlap on small screens. Resolve by the actual nearest
    // center, rather than SVG paint order, so every galaxy remains selectable.
    const nearest = field.galaxies.reduce(
      (best, galaxy) =>
        Math.hypot(galaxy.x - point.x, galaxy.y - point.y) <
        Math.hypot(best.x - point.x, best.y - point.y)
          ? galaxy
          : best,
      fallback,
    );
    onSelect(nearest);
  }

  return (
    <figure className="map-card">
      <figcaption className="map-heading">
        <div className="map-heading-toolbar">
          <div className="map-heading-label">
            <span className="status-dot" />
            OBSERVATION FIELD
          </div>
          <div className="image-mode-toggle" role="group" aria-label="Image display">
            <button type="button" aria-pressed={imageMode === "color"}
              onClick={() => { setImageMode("color"); setImageFailed(false); }}>
              Color
            </button>
            <button type="button" aria-pressed={imageMode === "grayscale"}
              onClick={() => { setImageMode("grayscale"); setImageFailed(false); }}>
              Black and white
            </button>
          </div>
        </div>
        <p>{imageCaption}</p>
      </figcaption>
      <div className="map-frame" ref={frame}>
        {imageFailed ? (
          <p className="image-error" role="alert">
            The field image could not be loaded. Reload to try again.
          </p>
        ) : (
          <svg
            ref={svgRef}
            className="galaxy-map"
            role="group"
            aria-label="GOODS-S interactive galaxy map"
            aria-describedby="map-instructions"
            data-testid="galaxy-map"
            viewBox={`-0.5 -0.5 ${field.width} ${field.height}`}
          >
            <title>
              {imageMode === "color"
                ? "GOODS-S F090W/F200W/F444W color image with selectable quality-A galaxies"
                : "GOODS-S F200W black-and-white image with selectable quality-A galaxies"}
            </title>
            {/* Pixel-center coordinates are integers; image edges lie at -0.5. */}
            <image
              href={imageMode === "color" ? colorImage : grayscaleImage}
              x={-0.5}
              y={-0.5}
              width={field.width}
              height={field.height}
              onError={() => setImageFailed(true)}
              aria-hidden="true"
            />
            {field.galaxies.map((galaxy) => {
              const selected = galaxy.galaxy_id === selectedId;
              return (
                <g
                  key={galaxy.galaxy_id}
                  id={`galaxy-${galaxy.galaxy_id}`}
                  className={`galaxy-marker${selected ? " is-selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select galaxy ${galaxy.galaxy_id}`}
                  aria-pressed={selected}
                  data-galaxy-id={galaxy.galaxy_id}
                  transform={`translate(${galaxy.x} ${galaxy.y})`}
                  onClick={(event) => selectNearest(event, galaxy)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(galaxy);
                    }
                  }}
                >
                  <circle className="marker-hit" r={hitRadius} />
                  <circle className="marker-ring" r={ringRadius} />
                  {selected && (
                    <circle
                      className="marker-selection"
                      r={ringRadius + 8 / scale}
                    />
                  )}
                  <g
                    className="marker-label"
                    transform={`translate(${ringRadius + 9 / scale} ${-9 / scale})`}
                    aria-hidden="true"
                    pointerEvents="none"
                  >
                    <text fontSize={11 / scale} strokeWidth={3 / scale}>
                      #{galaxy.shortId}
                    </text>
                  </g>
                </g>
              );
            })}
          </svg>
        )}
        <span className="image-corner-label" aria-hidden="true">
          JWST / NIRCam
        </span>
      </div>
      <div className="map-legend">
        <div>
          <span className="legend-ring" />
          <span>
            <strong>{field.galaxies.length} selectable galaxies</strong>
            <small>Quality A · highly robust spectroscopic redshifts</small>
          </span>
        </div>
        <span className="selected-legend">
          <span className="legend-ring selected" />
          Selected
        </span>
      </div>
      <p className="map-instructions" id="map-instructions">
        Click or tap a ring to inspect a galaxy. You can also Tab to a ring and
        press Enter.
      </p>
    </figure>
  );
}
