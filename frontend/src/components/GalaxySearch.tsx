import { useId, useRef, useState } from "react";
import type { SelectableGalaxy } from "../data/galaxies";

export function GalaxySearch({
  galaxies,
  onSelect,
}: {
  galaxies: SelectableGalaxy[];
  onSelect: (galaxy: SelectableGalaxy) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const inputId = useId();
  const container = useRef<HTMLDivElement>(null);
  const matches = galaxies.filter((g) =>
    g.galaxy_id.toLowerCase().includes(query.trim().toLowerCase()),
  );
  function choose(galaxy: SelectableGalaxy) {
    setOpen(false);
    setQuery("");
    setActive(-1);
    onSelect(galaxy);
  }
  function move(index: number) {
    setOpen(true);
    setActive(index);
    requestAnimationFrame(() =>
      document
        .getElementById(`${listId}-${index}`)
        ?.scrollIntoView({ block: "nearest" }),
    );
  }
  return (
    <div
      className="galaxy-search"
      ref={container}
      onBlur={(event) => {
        if (!container.current?.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor={inputId}>Find a galaxy</label>
      <input
        id={inputId}
        type="search"
        role="combobox"
        autoComplete="off"
        placeholder="Search any galaxy ID…"
        value={query}
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={
          open && active >= 0 && matches[active]
            ? `${listId}-${active}`
            : undefined
        }
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
            setActive(-1);
          } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            if (matches.length)
              move(
                event.key === "ArrowDown"
                  ? (active + 1) % matches.length
                  : active <= 0
                    ? matches.length - 1
                    : active - 1,
              );
          } else if (open && (event.key === "Home" || event.key === "End")) {
            event.preventDefault();
            if (matches.length)
              move(event.key === "Home" ? 0 : matches.length - 1);
          } else if (event.key === "Enter" && open && matches[active]) {
            event.preventDefault();
            choose(matches[active]);
          }
        }}
      />
      <span className="search-hint">
        All {galaxies.length} galaxies, including hidden rings
      </span>
      {open && (
        <div className="search-results">
          <span className="search-result-count" aria-live="polite">
            {matches.length
              ? `${matches.length} matching galaxies`
              : "No galaxies match this ID."}
          </span>
          <ul id={listId} role="listbox" aria-label="Matching galaxies">
            {matches.map((galaxy, index) => (
              <li
                id={`${listId}-${index}`}
                key={galaxy.galaxy_id}
                role="option"
                aria-selected={index === active}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(galaxy)}
              >
                {galaxy.galaxy_id}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
