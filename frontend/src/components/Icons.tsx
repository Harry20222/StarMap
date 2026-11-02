type IconProps = { className?: string };

export function FieldIcon({ className }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="20" cy="20" r="11" />
      <circle cx="20" cy="20" r="3" />
      <path d="M20 2v10m0 16v10M2 20h10m16 0h10" />
      <path d="m7 7 5 5m16 16 5 5m0-26-5 5M12 28l-5 5" opacity=".4" />
    </svg>
  );
}

export function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m6 6 12 12M6 18 18 6" />
    </svg>
  );
}

export function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10h12m-5-5 5 5-5 5" />
    </svg>
  );
}
