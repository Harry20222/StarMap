import { useEffect, useRef } from "react";
import { formatDistance, type SelectableGalaxy } from "../data/galaxies";
import { CloseIcon } from "./Icons";
import { Term } from "./InfoTip";

type GalaxyPopupProps = {
  galaxy: SelectableGalaxy;
  cosmology: string;
  onClose: () => void;
};

function coordinate(value: number | null) {
  return value === null ? "Unknown" : `${value.toFixed(6)}°`;
}

export function GalaxyPopup({ galaxy, cosmology, onClose }: GalaxyPopupProps) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    panel.current?.focus({ preventScroll: true });
    // On a phone the inspector follows the image, leaving the map unobstructed.
    if (window.matchMedia("(max-width: 980px)").matches) {
      panel.current?.scrollIntoView({ block: "nearest" });
    }
  }, [galaxy.galaxy_id]);

  return (
    <section
      className="inspector-panel galaxy-popup"
      ref={panel}
      role="dialog"
      aria-modal="false"
      aria-labelledby="galaxy-title"
      tabIndex={-1}
      data-testid="galaxy-popup"
    >
      <div className="inspector-topline">
        <span className="eyebrow">GALAXY INSPECTOR</span>
        <button
          className="icon-button"
          type="button"
          onClick={onClose}
          aria-label="Close galaxy details"
        >
          <CloseIcon />
        </button>
      </div>
      <div className="galaxy-identity">
        <div className="selected-badge">
          <span />
          SELECTED OBJECT
        </div>
        <h2 id="galaxy-title">Galaxy {galaxy.shortId}</h2>
        <p className="full-galaxy-id" data-testid="galaxy-id">
          {galaxy.galaxy_id}
        </p>
      </div>
      <div className="distance-block">
        <p>
          Estimated <Term name="Comoving distance">comoving distance</Term> from
          us
        </p>
        <h3
          data-testid="distance"
          data-distance-ly={galaxy.distance_from_us.value ?? "unknown"}
        >
          {formatDistance(galaxy.distance_from_us)}
        </h3>
        <span className="model-label">
          {cosmology} cosmological model · <Term name="Light-year" />
        </span>
      </div>
      <dl className="galaxy-details">
        <div>
          <dt>
            <Term name="Right ascension" /> <span>RA · ICRS</span>
          </dt>
          <dd data-testid="ra">{coordinate(galaxy.ra_deg)}</dd>
        </div>
        <div>
          <dt>
            <Term name="Declination" /> <span>Dec · ICRS</span>
          </dt>
          <dd data-testid="dec">{coordinate(galaxy.dec_deg)}</dd>
        </div>
        <div>
          <dt>
            <Term name="Spectroscopic redshift" /> <span>z</span>
          </dt>
          <dd data-testid="redshift">
            {galaxy.redshift?.toFixed(6) ?? "Unknown"}
          </dd>
        </div>
        <div>
          <dt>
            <Term name="Redshift quality" />
          </dt>
          <dd>
            <span className="quality-badge">{galaxy.redshift_quality}</span>
          </dd>
        </div>
        <div>
          <dt>
            <Term name="Redshift uncertainty" />
          </dt>
          <dd data-testid="redshift-uncertainty">
            {galaxy.redshift_uncertainty === null
              ? "not published"
              : galaxy.redshift_uncertainty.toLocaleString("en-US", {
                  maximumSignificantDigits: 6,
                })}
          </dd>
        </div>
      </dl>
      <p className="quality-description">{galaxy.redshift_quality_meaning}</p>
      <div className="distance-note">
        <span className="note-symbol">i</span>
        <p>
          A model-based estimate of comoving distance, distinct from
          light-travel time. Quality A describes the redshift identification; it
          is not a numerical error margin.
        </p>
      </div>
      <p className="dismiss-hint">
        Select another ring to explore. <kbd>Esc</kbd> to close.
      </p>
    </section>
  );
}
