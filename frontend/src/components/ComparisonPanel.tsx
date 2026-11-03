import { useEffect, useRef } from "react";
import {
  formatDistance,
  getComparison,
  type GalaxyField,
} from "../data/galaxies";
import { Term } from "./InfoTip";
import { CloseIcon } from "./Icons";

type ComparisonPanelProps = {
  field: GalaxyField;
  startId: string | null;
  pairIds: [string, string] | null;
  onClear: () => void;
};

export function ComparisonPanel({
  field,
  startId,
  pairIds,
  onClear,
}: ComparisonPanelProps) {
  const panel = useRef<HTMLElement>(null);
  const a = pairIds?.[0],
    b = pairIds?.[1];
  useEffect(() => {
    if (!a || !b) return;
    panel.current?.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 980px)").matches)
      panel.current?.scrollIntoView({ block: "nearest" });
  }, [a, b]);
  const pair = a && b ? getComparison(field, a, b) : null;
  return (
    <section
      ref={panel}
      className="inspector-panel comparison-panel"
      role="region"
      aria-label="Galaxy comparison"
      tabIndex={-1}
    >
      <div className="inspector-topline">
        <span className="eyebrow">GALAXY COMPARISON</span>
        <button
          type="button"
          className="icon-button"
          onClick={onClear}
          aria-label="Clear comparison"
        >
          <CloseIcon />
        </button>
      </div>
      {pair ? (
        <>
          <div className="comparison-identities">
            <h2>Galaxy separation</h2>
            <p>
              <strong>A</strong>
              <span data-testid="comparison-a">{a}</span>
            </p>
            <p>
              <strong>B</strong>
              <span data-testid="comparison-b">{b}</span>
            </p>
          </div>
          <dl className="comparison-measurements">
            <div>
              <dt>
                <Term name="Angular separation" />
              </dt>
              <dd
                data-testid="comparison-angle"
                data-value={pair.angular_separation.value ?? "unknown"}
              >
                {pair.angular_separation.value?.toFixed(8) ?? "Unknown"}°
              </dd>
            </div>
            <div>
              <dt>
                From us to A · <Term name="Comoving distance">comoving</Term>
              </dt>
              <dd
                data-testid="comparison-distance-a"
                data-value={pair.distance_from_us_a.value ?? "unknown"}
              >
                {formatDistance(pair.distance_from_us_a)}
              </dd>
            </div>
            <div>
              <dt>
                From us to B · <Term name="Comoving distance">comoving</Term>
              </dt>
              <dd
                data-testid="comparison-distance-b"
                data-value={pair.distance_from_us_b.value ?? "unknown"}
              >
                {formatDistance(pair.distance_from_us_b)}
              </dd>
            </div>
            <div className="separation-result">
              <dt>
                Estimated 3D{" "}
                <Term name="Comoving distance">comoving separation</Term>
              </dt>
              <dd
                data-testid="comparison-3d"
                data-value={pair.estimated_3d_separation.value ?? "unknown"}
              >
                {formatDistance(pair.estimated_3d_separation)}
              </dd>
            </div>
          </dl>
          <p className="comparison-model">
            <Term name="Light-year" /> ·{" "}
            <Term name="Planck18">{field.cosmology}</Term>
          </p>
          <p className="comparison-explanation">
            The line shows separation on the sky. The estimated 3D comoving
            separation also accounts for how far away each galaxy is. These are
            model-based estimates; uncertainties are not propagated.
          </p>
          <p className="dismiss-hint">
            Choose another pair, or press <kbd>Esc</kbd> to clear.
          </p>
        </>
      ) : (
        <div className="comparison-empty">
          <h2>{startId ? "Choose galaxy B." : "Connect two galaxies."}</h2>
          {startId && <p className="full-galaxy-id">A · {startId}</p>}
          <p>
            Drag from one visible ring to another, or select two rings in
            sequence. Click, tap, or use Tab and Enter.
          </p>
          <p>
            Releasing on empty sky or the starting galaxy cancels an unfinished
            line.
          </p>
        </div>
      )}
    </section>
  );
}
