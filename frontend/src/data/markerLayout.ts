import type { SelectableGalaxy } from "./galaxies";

const qualityRank: Record<string, number> = { A: 0, B: 1, C: 2, D: 3, E: 4 };

export function markerPriority(
  a: SelectableGalaxy,
  b: SelectableGalaxy,
): number {
  const quality =
    (qualityRank[a.redshift_quality ?? ""] ?? 99) -
    (qualityRank[b.redshift_quality ?? ""] ?? 99);
  if (quality) return quality;
  const sa = a.apparent_size_arcsec,
    sb = b.apparent_size_arcsec;
  if (
    sa != null &&
    sb != null &&
    Number.isFinite(sa) &&
    Number.isFinite(sb) &&
    sa > 0 &&
    sb > 0 &&
    a.apparent_size_measurement &&
    a.apparent_size_measurement === b.apparent_size_measurement &&
    sa !== sb
  )
    return sb - sa;
  return a.galaxy_id < b.galaxy_id ? -1 : a.galaxy_id > b.galaxy_id ? 1 : 0;
}

export function layoutMarkers(
  galaxies: SelectableGalaxy[],
  imageWidth: number,
  displayWidth: number,
) {
  const scale = Math.max(displayWidth / imageWidth, 0.001);
  const ringRadius = Math.max(17, 6 / scale);
  const highlightRadius = ringRadius + 4 / scale;
  // Reserve the largest possible selected outline, its stroke, and a small gap.
  const clearance = 2 * highlightRadius + 3 / scale;
  const ranked = [...galaxies]
    .sort((a, b) => (a.galaxy_id < b.galaxy_id ? -1 : 1))
    .sort(markerPriority);
  const accepted: SelectableGalaxy[] = [];
  for (const galaxy of ranked) {
    if (
      accepted.every(
        (other) =>
          Math.hypot(galaxy.x - other.x, galaxy.y - other.y) >= clearance,
      )
    )
      accepted.push(galaxy);
  }
  const ids = new Set(accepted.map((g) => g.galaxy_id));
  return {
    visible: galaxies.filter((g) => ids.has(g.galaxy_id)),
    hiddenCount: galaxies.length - accepted.length,
    scale,
    ringRadius,
    highlightRadius,
    hitRadius: Math.max(ringRadius + 9 / scale, 22 / scale),
    clearance,
  };
}
