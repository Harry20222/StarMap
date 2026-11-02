import { useCallback, useEffect, useState } from "react";
import type { GalaxyField, SelectableGalaxy } from "./data/galaxies";
import { GalaxyMap } from "./components/GalaxyMap";
import { GalaxyPopup } from "./components/GalaxyPopup";
import { ArrowIcon, FieldIcon } from "./components/Icons";

export function App({ field }: { field: GalaxyField }) {
  const [selected, setSelected] = useState<SelectableGalaxy | null>(null);
  const closeSelection = useCallback(() => {
    const id = selected?.galaxy_id;
    setSelected(null);
    if (id)
      requestAnimationFrame(() =>
        document.getElementById(`galaxy-${id}`)?.focus({ preventScroll: true }),
      );
  }, [selected]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && selected) {
        event.preventDefault();
        closeSelection();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, closeSelection]);

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#main">
          <FieldIcon />
          <span>
            StarMap<span className="brand-divider">/</span>
            <small>FIELD EXPLORER</small>
          </span>
        </a>
        <span className="header-note">
          <span className="status-dot" />
          REAL SKY. REAL GALAXIES.
        </span>
      </header>
      <main id="main">
        <section className="page-intro">
          <div>
            <p className="eyebrow">A WINDOW INTO THE DISTANT UNIVERSE</p>
            <h1>
              Explore GOODS-S<span>.</span>
            </h1>
          </div>
          <p className="intro-description">
            Every ring marks a galaxy with a highly robust spectroscopic
            redshift. Select one to discover its estimated distance from us.
          </p>
        </section>
        <div className="workspace">
          <GalaxyMap
            field={field}
            selectedId={selected?.galaxy_id ?? null}
            onSelect={setSelected}
          />
          <aside className="inspector-column" aria-label="Galaxy information">
            {selected ? (
              <GalaxyPopup
                galaxy={selected}
                cosmology={field.cosmology}
                onClose={closeSelection}
              />
            ) : (
              <section className="inspector-panel empty-inspector">
                <div className="inspector-topline">
                  <span className="eyebrow">GALAXY INSPECTOR</span>
                  <span className="subtle-index">01</span>
                </div>
                <div className="empty-message">
                  <div className="empty-target">
                    <FieldIcon />
                  </div>
                  <p className="eyebrow">YOUR EXPLORATION STARTS HERE</p>
                  <h2>Choose a galaxy.</h2>
                  <p>
                    Click a ring in the field to reveal a galaxy’s redshift, sky
                    position, and estimated distance.
                  </p>
                  <span className="empty-prompt">
                    Follow the rings <ArrowIcon />
                  </span>
                </div>
                <div className="field-facts">
                  <div>
                    <span>SELECTABLE OBJECTS</span>
                    <strong>
                      {field.galaxies.length}
                      <small>quality A</small>
                    </strong>
                  </div>
                  <div>
                    <span>DISTANCE MODEL</span>
                    <strong>
                      {field.cosmology}
                      <small>comoving</small>
                    </strong>
                  </div>
                </div>
              </section>
            )}
            <div className="field-note">
              <p className="eyebrow">LOOKING DEEPER</p>
              <p>
                This small patch of sky holds galaxies billions of light-years
                away. Nearby on the image can still mean far apart in space.
              </p>
            </div>
            <div className="source-note">
              <span>
                IMAGE / {field.dataset.image_release}{" "}
                {field.dataset.image_version}
              </span>
              <span>
                CATALOG / {field.dataset.catalog_release}{" "}
                {field.dataset.catalog_version}
              </span>
            </div>
          </aside>
        </div>
        <footer className="page-footer">
          <p>NASA / ESA / CSA · JWST · JADES collaboration</p>
          <a
            href="https://archive.stsci.edu/hlsp/jades"
            target="_blank"
            rel="noreferrer"
          >
            Explore the source data <ArrowIcon />
          </a>
        </footer>
      </main>
    </div>
  );
}
