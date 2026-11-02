import markersExport from "../../../results/markers.json" with { type: "json" };
import measurementsExport from "../../../results/measurements.json" with { type: "json" };

export type Distance = {
  value: number | null;
  unit: string;
  convention: string;
};

export type GalaxyRecord = {
  galaxy_id: string;
  nirspec_id: number | null;
  nircam_id: number | null;
  tier: string | null;
  ra_deg: number | null;
  dec_deg: number | null;
  redshift: number | null;
  redshift_quality: string | null;
  redshift_quality_meaning: string;
  redshift_uncertainty: number | null;
  distance_from_us: Distance;
};

export type MarkerExport = {
  shape_yx: number[];
  pixel_origin: number;
  display_origin: string;
  markers: { galaxy_id: string; x: number; y: number; inside_image: boolean }[];
};

export type MeasurementExport = {
  cosmology: { name: string };
  dataset: {
    field: string;
    filter: string;
    image_release: string;
    catalog_release: string;
    image_version: string;
    catalog_version: string;
  };
  galaxies: GalaxyRecord[];
};

export type SelectableGalaxy = GalaxyRecord & {
  x: number;
  y: number;
  shortId: string;
};
export type GalaxyField = {
  width: number;
  height: number;
  label: string;
  cosmology: string;
  dataset: MeasurementExport["dataset"];
  galaxies: SelectableGalaxy[];
};

export function joinGalaxyData(
  markers: MarkerExport,
  measurements: MeasurementExport,
): GalaxyField {
  const [height, width] = markers.shape_yx;
  if (
    markers.shape_yx.length !== 2 ||
    !Number.isInteger(width) ||
    !Number.isInteger(height) ||
    width <= 0 ||
    height <= 0 ||
    markers.pixel_origin !== 0 ||
    markers.display_origin !== "lower"
  ) {
    throw new Error("The image coordinate information is not supported.");
  }
  const byId = new Map(
    measurements.galaxies.map((galaxy) => [galaxy.galaxy_id, galaxy]),
  );
  if (byId.size !== measurements.galaxies.length)
    throw new Error("The galaxy catalog has duplicate IDs.");
  const seen = new Set<string>();
  const galaxies: SelectableGalaxy[] = [];
  for (const marker of markers.markers) {
    if (seen.has(marker.galaxy_id))
      throw new Error("The image positions have duplicate galaxy IDs.");
    seen.add(marker.galaxy_id);
    const galaxy = byId.get(marker.galaxy_id);
    if (!galaxy)
      throw new Error("The galaxy catalog and image positions do not match.");
    if (galaxy.redshift_quality !== "A" || !marker.inside_image) continue;
    if (
      ![marker.x, marker.y].every(Number.isFinite) ||
      marker.x < -0.5 ||
      marker.x >= width - 0.5 ||
      marker.y < -0.5 ||
      marker.y >= height - 0.5
    ) {
      throw new Error("A selectable galaxy falls outside the image.");
    }
    if (
      !galaxy.distance_from_us ||
      galaxy.distance_from_us.unit !== "ly" ||
      galaxy.distance_from_us.convention !== "comoving"
    ) {
      throw new Error(
        "Comoving galaxy distances are missing from the exported catalog.",
      );
    }
    const distance = galaxy.distance_from_us.value;
    if (distance !== null && (!Number.isFinite(distance) || distance < 0)) {
      throw new Error("A galaxy distance is invalid.");
    }
    galaxies.push({
      ...galaxy,
      x: marker.x,
      y: height - 1 - marker.y,
      shortId: galaxy.nirspec_id?.toString() ?? galaxy.galaxy_id,
    });
  }
  const dataset = measurements.dataset;
  return {
    width,
    height,
    dataset,
    galaxies,
    cosmology: measurements.cosmology.name,
    label: `${dataset.field} · ${dataset.filter} image (${dataset.image_release}) · galaxy catalog (${dataset.catalog_release}).`,
  };
}

export function loadGalaxyField(): GalaxyField {
  // Import the backend exports directly. Vite bundles them; no Python API is involved.
  return joinGalaxyData(markersExport, measurementsExport);
}

export function formatDistance(distance: Distance): string {
  if (distance.value === null) return "Unknown";
  const value = distance.value;
  if (value >= 1e9)
    return `about ${(value / 1e9).toLocaleString("en-US", { maximumFractionDigits: 1 })} billion light-years`;
  if (value >= 1e6)
    return `about ${(value / 1e6).toLocaleString("en-US", { maximumFractionDigits: 1 })} million light-years`;
  return `about ${value.toLocaleString("en-US", { maximumFractionDigits: 0 })} light-years`;
}
