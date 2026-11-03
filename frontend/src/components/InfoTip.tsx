import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

export const definitions = {
  "Light-year":
    "A unit of distance: how far light travels in one year, about 9.46 trillion kilometres. A distance in light-years is a length, not an age or travel time.",
  "Redshift quality":
    "A flag describing confidence that the spectroscopic redshift was correctly identified. A is highly robust in this JADES catalog. The flag does not give a numerical error margin or an accuracy percentage.",
  "Right ascension":
    "The east–west coordinate of a position on the sky, similar to longitude on Earth. This map reports right ascension in degrees in the ICRS celestial reference frame.",
  Declination:
    "The north–south coordinate of a position on the sky, similar to latitude. Positive degrees are north of the celestial equator; negative degrees are south.",
  "Spectroscopic redshift":
    "The stretching of a galaxy’s light to longer wavelengths, measured from features in its spectrum. The value z is dimensionless. A cosmological model converts it into an estimated distance.",
  "Angular separation":
    "The angle between two directions on the sky, shown here in degrees. It tells you how far apart two galaxies appear, but not their full separation in space.",
  "Comoving distance":
    "A model-based distance that accounts for cosmic expansion using one shared coordinate scale, with today’s scale factor set to one. It is distinct from light-travel time and from distance at the time the light was emitted.",
  "Redshift uncertainty":
    "A published numerical uncertainty in the measured redshift, when available. This catalog does not publish it for these records. It cannot be inferred from the redshift quality flag.",
  Planck18:
    "The Astropy cosmological model used by this project to convert redshift into comoving distance. All exported pair measurements use the same model.",
} as const;
export type ScientificTerm = keyof typeof definitions;

export function InfoTip({ term }: { term: ScientificTerm }) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 12, width: 280 });
  const button = useRef<HTMLButtonElement>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  const id = useId();
  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = button.current?.getBoundingClientRect();
      if (!rect) return;
      const width = Math.min(280, window.innerWidth - 24);
      const height = tooltip.current?.offsetHeight ?? 140;
      setPosition({
        width,
        left: Math.max(
          12,
          Math.min(
            rect.left + rect.width / 2 - width / 2,
            window.innerWidth - width - 12,
          ),
        ),
        top:
          rect.bottom + height + 8 <= window.innerHeight - 12
            ? rect.bottom + 8
            : Math.max(12, rect.top - height - 8),
      });
    };
    update();
    window.addEventListener("resize", update);
    document.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      document.removeEventListener("scroll", update, true);
    };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!button.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        event.stopPropagation();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape, true);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape, true);
    };
  }, [open]);
  return (
    <>
      <button
        ref={button}
        type="button"
        className="info-button"
        aria-label={`About ${term}`}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => {
          if (document.activeElement !== button.current) setOpen(false);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen(true)}
      >
        <span aria-hidden="true">i</span>
      </button>
      {open &&
        createPortal(
          <div
            id={id}
            ref={tooltip}
            className="science-tooltip"
            role="tooltip"
            style={position}
          >
            <strong>{term}</strong>
            <p>{definitions[term]}</p>
          </div>,
          document.body,
        )}
    </>
  );
}

export function Term({
  name,
  children,
}: {
  name: ScientificTerm;
  children?: ReactNode;
}) {
  return (
    <span className="scientific-term">
      {children ?? name}
      <InfoTip term={name} />
    </span>
  );
}
