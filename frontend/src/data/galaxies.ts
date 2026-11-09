import { imageSources } from "./imageAssets";

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
  apparent_size_arcsec?: number | null;
  apparent_size_measurement?: string | null;
};

export type PairMeasurement = {
  galaxy_a_id: string;
  galaxy_b_id: string;
  status: string;
  angular_separation: { value: number | null; unit: string };
  distance_from_us_a: Distance;
  distance_from_us_b: Distance;
  estimated_3d_separation: Distance;
};

export type ImageAssets = Record<"color" | "grayscale", { asset: string; width: number }[]>;

export type MapMetadata = {
  map_id: string;
  shape_yx: number[];
  pixel_origin: number;
  display_origin: string;
  image_assets: ImageAssets;
  cosmology: { name: string };
  dataset: {
    field: string;
    filter: string;
    image_release: string;
    catalog_release: string;
    image_version: string;
    catalog_version: string;
  };
};

export type MapCatalog = {
  map_id: string;
  galaxies: GalaxyRecord[];
  markers: { galaxy_id: string; x: number; y: number; inside_image: boolean }[];
};

export type SelectableGalaxy = GalaxyRecord & { x: number; y: number; shortId: string };
export type GalaxyField = {
  mapId: string;
  width: number;
  height: number;
  imageAssets: ImageAssets;
  label: string;
  cosmology: string;
  dataset: MapMetadata["dataset"];
  galaxies: SelectableGalaxy[];
};

export function joinGalaxyData(metadata: MapMetadata, catalog: MapCatalog): GalaxyField {
  const [height, width] = metadata.shape_yx;
  if (metadata.shape_yx.length !== 2 || !Number.isInteger(width) || !Number.isInteger(height) ||
      width <= 0 || height <= 0 || metadata.pixel_origin !== 0 || metadata.display_origin !== "lower")
    throw new Error("The image coordinate information is not supported.");
  if (metadata.map_id !== catalog.map_id || metadata.cosmology.name !== "Planck18")
    throw new Error("The map and galaxy catalog do not match.");
  for (const mode of ["color", "grayscale"] as const) {
    const variants = metadata.image_assets[mode];
    if (!variants?.length || variants.some((v, i) => !Number.isInteger(v.width) || v.width <= 0 || !imageSources[v.asset] ||
        (i > 0 && v.width <= variants[i - 1].width)))
      throw new Error("The map image assets are invalid.");
  }
  const byId = new Map(catalog.galaxies.map((g) => [g.galaxy_id, g]));
  if (byId.size !== catalog.galaxies.length) throw new Error("The galaxy catalog has duplicate IDs.");
  const seen = new Set<string>();
  const galaxies: SelectableGalaxy[] = [];
  for (const marker of catalog.markers) {
    if (seen.has(marker.galaxy_id)) throw new Error("The image positions have duplicate galaxy IDs.");
    seen.add(marker.galaxy_id);
    const galaxy = byId.get(marker.galaxy_id);
    if (!galaxy) throw new Error("The galaxy catalog and image positions do not match.");
    if (galaxy.redshift_quality !== "A" || !marker.inside_image) continue;
    if (![marker.x, marker.y].every(Number.isFinite) || marker.x < -0.5 || marker.x >= width - 0.5 ||
        marker.y < -0.5 || marker.y >= height - 0.5)
      throw new Error("A selectable galaxy falls outside the image.");
    const distance = galaxy.distance_from_us;
    if (!distance || distance.unit !== "ly" || distance.convention !== "comoving" ||
        (distance.value !== null && (!Number.isFinite(distance.value) || distance.value < 0)))
      throw new Error("A galaxy comoving distance is invalid.");
    galaxies.push({ ...galaxy, x: marker.x, y: height - 1 - marker.y,
      shortId: galaxy.nirspec_id?.toString() ?? galaxy.galaxy_id });
  }
  if (seen.size !== byId.size) throw new Error("The galaxy catalog and image positions do not match.");
  const dataset = metadata.dataset;
  return { mapId: metadata.map_id, width, height, imageAssets: metadata.image_assets, dataset, galaxies,
    cosmology: metadata.cosmology.name,
    label: `${dataset.field} · ${dataset.filter} image (${dataset.image_release}) · galaxy catalog (${dataset.catalog_release}).` };
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
