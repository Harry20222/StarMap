import { useCallback, useEffect, useState } from "react";
import type { GalaxyField, SelectableGalaxy } from "./data/galaxies";
import { GalaxyMap } from "./components/GalaxyMap";
import { GalaxyPopup } from "./components/GalaxyPopup";
import { ArrowIcon, FieldIcon } from "./components/Icons";
import { ComparisonPanel } from "./components/ComparisonPanel";
import { Term } from "./components/InfoTip";

export function App({ field }: { field: GalaxyField }) {
  const [selected, setSelected] = useState<SelectableGalaxy | null>(null);
  const [mode, setMode] = useState<"inspect" | "compare">("inspect");
  const [startId, setStartId] = useState<string | null>(null);
  const [pairIds, setPairIds] = useState<[string, string] | null>(null);
  const clearComparison = useCallback(() => {
    setStartId(null);
    setPairIds(null);
  }, []);
  const changeMode = (next: "inspect" | "compare") => {
    if (next === mode) return;
    setMode(next);
    setSelected(null);
    clearComparison();
  };
  const completePair = (a: string, b: string) => {
    if (
      a === b ||
      ![a, b].every((id) => field.galaxies.some((g) => g.galaxy_id === id))
    ) {
      clearComparison();
      return;
    }
    setPairIds([a, b]);
    setStartId(null);
  };
  const chooseGalaxy = (galaxy: SelectableGalaxy) => {
    if (mode === "inspect") {
      setSelected(galaxy);
      return;
    }
    if (!startId) {
      setStartId(galaxy.galaxy_id);
      setPairIds(null);
    } else if (startId === galaxy.galaxy_id) clearComparison();
    else completePair(startId, galaxy.galaxy_id);
  };
  const closeSelection = useCallback(() => {
    const id = selected?.galaxy_id;
    setSelected(null);
    if (id)
      requestAnimationFrame(() =>
        (
          document.getElementById(`galaxy-${id}`) ??
          document.querySelector<HTMLInputElement>('input[role="combobox"]')
        )?.focus({ preventScroll: true }),
      );
  }, [selected]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (
        event.key === "Escape" &&
        mode === "compare" &&
        (startId || pairIds)
      ) {
        event.preventDefault();
        clearComparison();
      } else if (event.key === "Escape" && selected) {
        event.preventDefault();
        closeSelection();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selected, closeSelection, mode, startId, pairIds, clearComparison]);

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
            Every ring marks a galaxy with a highly robust{" "}
            <Term name="Spectroscopic redshift">spectroscopic redshift</Term>.
            Inspect one galaxy or compare two to explore their estimated
            distances.
          </p>
        </section>
        <div className="workspace">
          <GalaxyMap
            field={field}
            selectedId={selected?.galaxy_id ?? null}
            onSelect={chooseGalaxy}
            mode={mode}
            onModeChange={changeMode}
            startId={startId}
            pairIds={pairIds}
            onCompareStart={(id) => {
              setStartId(id);
              setPairIds(null);
            }}
            onCompareComplete={completePair}
            onCompareCancel={clearComparison}
            onExamplePair={
              ["goods-s-deephst:21598", "goods-s-deephst:21842"].every((id) =>
                field.galaxies.some((g) => g.galaxy_id === id),
              )
                ? () =>
                    completePair(
                      "goods-s-deephst:21598",
                      "goods-s-deephst:21842",
                    )
                : undefined
            }
          />
          <aside className="inspector-column" aria-label="Galaxy information">
            {mode === "compare" ? (
              <ComparisonPanel
                field={field}
                startId={startId}
                pairIds={pairIds}
                onClear={clearComparison}
              />
            ) : selected ? (
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
                    <span>CATALOG OBJECTS</span>
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
                This small patch of sky holds galaxies billions of{" "}
                <Term name="Light-year">light-years</Term> away. Nearby on the
                image can still mean far apart in space.
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
