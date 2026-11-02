import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { loadGalaxyField } from "./data/galaxies";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles.css";

const root = createRoot(document.getElementById("root")!);
try {
  const field = loadGalaxyField();
  root.render(
    <StrictMode>
      <App field={field} />
    </StrictMode>,
  );
} catch (error) {
  root.render(
    <main className="load-error" role="alert">
      <h1>The field could not be loaded.</h1>
      <p>
        {error instanceof Error
          ? error.message
          : "The field data is unavailable."}
      </p>
    </main>,
  );
}
