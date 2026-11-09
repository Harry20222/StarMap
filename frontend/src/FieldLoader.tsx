import { useEffect, useState } from "react";
import { App } from "./App";
import { loadGalaxyField } from "./data/api";
import type { GalaxyField } from "./data/galaxies";

export function FieldLoader() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ field?: GalaxyField; error?: string; empty?: boolean }>({});
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({});
    loadGalaxyField(controller.signal).then(
      (field) => { if (active) setState(field?.galaxies.length ? { field } : { empty: true }); },
      (error: unknown) => { if (active) setState({ error: error instanceof Error ? error.message : "The field data is unavailable." }); },
    );
    return () => { active = false; controller.abort(); };
  }, [attempt]);
  if (state.field) return <App field={state.field} />;
  return <main className="load-error" aria-live="polite" aria-busy={!state.error && !state.empty}>
    <h1>{state.error ? "The field could not be loaded." : state.empty ? "No galaxies are available." : "Loading the field…"}</h1>
    {state.error && <p role="alert">{state.error}</p>}
    {state.empty && <p>No maps or eligible galaxies were found in the catalog.</p>}
    {(state.error || state.empty) && <button className="retry-button" onClick={() => setAttempt((n) => n + 1)}>Retry</button>}
  </main>;
}
