import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent,
  type PointerEvent,
} from "react";
import colorImage from "../../../results/goods_s_color.png?url";
import grayscaleImage from "../../../results/goods_s_f200w.png?url";
import type { GalaxyField, SelectableGalaxy } from "../data/galaxies";
import { layoutMarkers } from "../data/markerLayout";
import { Term } from "./InfoTip";

type Point = { x: number; y: number };
type GalaxyMapProps = {
  field: GalaxyField;
  selectedId: string | null;
  onSelect: (galaxy: SelectableGalaxy) => void;
  mode: "inspect" | "compare";
  onModeChange: (mode: "inspect" | "compare") => void;
  startId: string | null;
  pairIds: [string, string] | null;
  onCompareStart: (id: string) => void;
  onCompareComplete: (a: string, b: string) => void;
  onCompareCancel: () => void;
  onVisibleChange: (ids: string[]) => void;
  notice: string;
};

export function GalaxyMap({
  field,
  selectedId,
  onSelect,
  mode,
  onModeChange,
  startId,
  pairIds,
  onCompareStart,
  onCompareComplete,
  onCompareCancel,
  onVisibleChange,
  notice,
}: GalaxyMapProps) {
  const [imageMode, setImageMode] = useState<"color" | "grayscale">("color");
  const [displayWidth, setDisplayWidth] = useState(800);
  const [imageFailed, setImageFailed] = useState(false);
  const [preview, setPreview] = useState<{
    startId: string;
    point: Point;
  } | null>(null);
  const frame = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<{
    pointerId: number;
    startId: string;
    clientX: number;
    clientY: number;
    moved: boolean;
  } | null>(null);
  const suppressClick = useRef(false);
  const layout = useMemo(
    () => layoutMarkers(field.galaxies, field.width, displayWidth),
    [field.galaxies, field.width, displayWidth],
  );
  const signature = layout.visible.map((g) => g.galaxy_id).join("|");
  useEffect(() => {
    onVisibleChange(layout.visible.map((g) => g.galaxy_id));
  }, [signature, onVisibleChange]);
  useEffect(() => {
    if (!frame.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setDisplayWidth(entry.contentRect.width),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (
      drag.current &&
      (mode !== "compare" ||
        !layout.visible.some((g) => g.galaxy_id === drag.current?.startId))
    ) {
      drag.current = null;
      setPreview(null);
      onCompareCancel();
    }
  }, [mode, signature, onCompareCancel]);

  const imageCaption =
    imageMode === "color"
      ? `${field.dataset.field} · F090W (blue) + F200W (green) + F444W (red) color image (${field.dataset.image_release}) · galaxy catalog (${field.dataset.catalog_release}).`
      : `${field.dataset.field} · F200W black-and-white image (${field.dataset.image_release}) · galaxy catalog (${field.dataset.catalog_release}).`;

  function skyPoint(event: { clientX: number; clientY: number }): Point | null {
    const matrix = svgRef.current?.getScreenCTM();
    if (!matrix) return null;
    return new DOMPoint(event.clientX, event.clientY).matrixTransform(
      matrix.inverse(),
    );
  }
  function nearest(point: Point | null) {
    if (!point) return null;
    let best: SelectableGalaxy | null = null;
    let distance = layout.hitRadius;
    for (const galaxy of layout.visible) {
      const next = Math.hypot(point.x - galaxy.x, point.y - galaxy.y);
      if (next <= distance) {
        best = galaxy;
        distance = next;
      }
    }
    return best;
  }
  function inspectClick(
    event: MouseEvent<SVGGElement>,
    fallback: SelectableGalaxy,
  ) {
    onSelect(
      event.detail === 0 ? fallback : (nearest(skyPoint(event)) ?? fallback),
    );
  }
  function pointerDown(
    event: PointerEvent<SVGGElement>,
    fallback: SelectableGalaxy,
  ) {
    suppressClick.current = false;
    if (mode !== "compare" || event.button !== 0) return;
    event.preventDefault();
    const galaxy = nearest(skyPoint(event)) ?? fallback;
    drag.current = {
      pointerId: event.pointerId,
      startId: galaxy.galaxy_id,
      clientX: event.clientX,
      clientY: event.clientY,
      moved: false,
    };
    svgRef.current?.setPointerCapture(event.pointerId);
  }
  function pointerMove(event: PointerEvent<SVGSVGElement>) {
    const current = drag.current;
    if (!current || event.pointerId !== current.pointerId) return;
    if (
      !current.moved &&
      Math.hypot(
        event.clientX - current.clientX,
        event.clientY - current.clientY,
      ) < 4
    )
      return;
    if (!current.moved) {
      current.moved = true;
      onCompareStart(current.startId);
    }
    const point = skyPoint(event);
    if (point) setPreview({ startId: current.startId, point });
  }
  function pointerUp(event: PointerEvent<SVGSVGElement>) {
    const current = drag.current;
    if (!current || current.pointerId !== event.pointerId) return;
    drag.current = null;
    setPreview(null);
    suppressClick.current = true;
    if (svgRef.current?.hasPointerCapture(event.pointerId))
      svgRef.current.releasePointerCapture(event.pointerId);
    if (!current.moved) {
      const galaxy = layout.visible.find(
        (g) => g.galaxy_id === current.startId,
      );
      if (galaxy) onSelect(galaxy);
      return;
    }
    const target = nearest(skyPoint(event));
    if (target && target.galaxy_id !== current.startId)
      onCompareComplete(current.startId, target.galaxy_id);
    else onCompareCancel();
  }
  function pointerCancel() {
    if (drag.current) {
      drag.current = null;
      setPreview(null);
      onCompareCancel();
    }
  }
  const source = layout.visible.find(
    (g) => g.galaxy_id === (preview?.startId ?? pairIds?.[0]),
  );
  const destination =
    preview?.point ?? layout.visible.find((g) => g.galaxy_id === pairIds?.[1]);
  const progress =
    notice ||
    (mode === "inspect"
      ? "Click or tap a ring to inspect a galaxy."
      : startId
        ? `Galaxy A selected: ${startId}. Choose galaxy B.`
        : pairIds
          ? "Comparison complete. Select or drag to start another pair."
          : "Drag between two rings, or select galaxy A then galaxy B.");

  return (
    <figure className="map-card">
      <figcaption className="map-heading">
        <div className="map-heading-toolbar">
          <div className="map-heading-label">
            <span className="status-dot" />
            OBSERVATION FIELD
          </div>
          <div
            className="image-mode-toggle"
            role="group"
            aria-label="Image display"
          >
            <button
              type="button"
              aria-pressed={imageMode === "color"}
              onClick={() => {
                setImageMode("color");
                setImageFailed(false);
              }}
            >
              Color
            </button>
            <button
              type="button"
              aria-pressed={imageMode === "grayscale"}
              onClick={() => {
                setImageMode("grayscale");
                setImageFailed(false);
              }}
            >
              Black and white
            </button>
          </div>
        </div>
        <p>{imageCaption}</p>
        <div className="interaction-toolbar">
          <div
            className="image-mode-toggle"
            role="group"
            aria-label="Map interaction"
          >
            <button
              type="button"
              aria-pressed={mode === "inspect"}
              onClick={() => onModeChange("inspect")}
            >
              Inspect
            </button>
            <button
              type="button"
              aria-pressed={mode === "compare"}
              onClick={() => onModeChange("compare")}
            >
              Compare
            </button>
          </div>
          <span>
            {mode === "compare"
              ? "Connect two visible galaxies"
              : "Explore one galaxy at a time"}
          </span>
        </div>
      </figcaption>
      <div className="map-frame" ref={frame}>
        {imageFailed ? (
          <p className="image-error" role="alert">
            The field image could not be loaded. Switch image mode or reload to
            try again.
          </p>
        ) : (
          <svg
            ref={svgRef}
            className={`galaxy-map ${mode === "compare" ? "compare-map" : ""}`}
            role="group"
            aria-label="GOODS-S interactive galaxy map"
            aria-describedby="map-instructions"
            data-testid="galaxy-map"
            viewBox={`-0.5 -0.5 ${field.width} ${field.height}`}
            onPointerMove={pointerMove}
            onPointerUp={pointerUp}
            onPointerCancel={pointerCancel}
            onClickCapture={(event) => {
              if (suppressClick.current) {
                suppressClick.current = false;
                event.preventDefault();
                event.stopPropagation();
              }
            }}
            onPointerDown={(event) => {
              if (
                mode === "compare" &&
                startId &&
                !(event.target as Element).closest(".galaxy-marker")
              )
                onCompareCancel();
            }}
          >
            <title>
              {imageMode === "color"
                ? "GOODS-S F090W/F200W/F444W color image"
                : "GOODS-S F200W black-and-white image"}{" "}
              with selectable quality-A galaxies
            </title>
            <image
              href={imageMode === "color" ? colorImage : grayscaleImage}
              x={-0.5}
              y={-0.5}
              width={field.width}
              height={field.height}
              onError={() => setImageFailed(true)}
              aria-hidden="true"
            />
            {source && destination && (
              <line
                className={`comparison-line${preview ? " is-provisional" : ""}`}
                data-testid="comparison-line"
                x1={source.x}
                y1={source.y}
                x2={destination.x}
                y2={destination.y}
                vectorEffect="non-scaling-stroke"
                pointerEvents="none"
              />
            )}
            {layout.visible.map((galaxy) => {
              const selected =
                selectedId === galaxy.galaxy_id ||
                startId === galaxy.galaxy_id ||
                pairIds?.includes(galaxy.galaxy_id);
              return (
                <g
                  key={galaxy.galaxy_id}
                  id={`galaxy-${galaxy.galaxy_id}`}
                  className={`galaxy-marker${selected ? " is-selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`Select galaxy ${galaxy.galaxy_id}`}
                  aria-pressed={Boolean(selected)}
                  data-galaxy-id={galaxy.galaxy_id}
                  data-clearance={layout.clearance}
                  transform={`translate(${galaxy.x} ${galaxy.y})`}
                  onPointerDown={(event) => pointerDown(event, galaxy)}
                  onClick={(event) => inspectClick(event, galaxy)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(galaxy);
                    }
                  }}
                >
                  <circle className="marker-hit" r={layout.hitRadius} />
                  <circle className="marker-ring" r={layout.ringRadius} />
                  {selected && (
                    <circle
                      className="marker-selection"
                      r={layout.highlightRadius}
                    />
                  )}
                  <g
                    className="marker-label"
                    transform={`translate(${layout.ringRadius + 9 / layout.scale} ${-9 / layout.scale})`}
                    aria-hidden="true"
                    pointerEvents="none"
                  >
                    <text
                      fontSize={11 / layout.scale}
                      strokeWidth={3 / layout.scale}
                    >
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
            <strong data-testid="visible-count">
              {layout.visible.length} visible of {field.galaxies.length}{" "}
              galaxies
            </strong>
            <small>
              <Term name="Redshift quality">Quality A</Term> · highly robust
              spectroscopic redshifts
            </small>
          </span>
        </div>
        <span className="selected-legend">
          <span className="legend-ring selected" />
          Selected
        </span>
      </div>
      <p className="overlap-note">
        {layout.hiddenCount} hidden to prevent overlapping rings. Larger
        apparent galaxies take priority; all records remain in the catalog.
      </p>
      <p
        className="map-instructions"
        id="map-instructions"
        role="status"
        aria-live="polite"
      >
        {progress} Tab and Enter/Space also select rings.
      </p>
    </figure>
  );
}
