import { joinGalaxyData, type GalaxyField, type MapCatalog, type MapMetadata, type PairMeasurement } from "./galaxies";

async function request<T>(path: string, signal: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal.addEventListener("abort", abort, { once: true });
  if (signal.aborted) controller.abort();
  const timer = window.setTimeout(abort, 15000);
  try {
    const response = await fetch(path, { signal: controller.signal, headers: { Accept: "application/json" } });
    if (!response.ok) {
      // Keep server/proxy diagnostics out of the page.
      throw new Error(response.status === 503
        ? "The catalog database is unavailable. Please retry shortly."
        : "The requested catalog data could not be loaded. Please retry.");
    }
    return await response.json() as T;
  } catch (error) {
    if (signal.aborted) throw error;
    if (error instanceof Error && error.message.startsWith("The ")) throw error;
    throw new Error("The Python API could not be reached. Please retry.");
  } finally {
    window.clearTimeout(timer);
    signal.removeEventListener("abort", abort);
  }
}

export async function loadGalaxyField(signal: AbortSignal, selectedMapId?: string): Promise<GalaxyField | null> {
  const { maps } = await request<{ maps: { map_id: string }[] }>("/api/maps", signal);
  if (!Array.isArray(maps)) throw new Error("The map list is invalid.");
  if (!maps.length) return null;
  const id = selectedMapId ?? maps.find((map) => map.map_id === "goods-s")?.map_id ?? maps[0].map_id;
  const path = `/api/maps/${encodeURIComponent(id)}`;
  const [metadata, catalog] = await Promise.all([
    request<MapMetadata>(path, signal), request<MapCatalog>(`${path}/galaxies`, signal),
  ]);
  return joinGalaxyData(metadata, catalog);
}

export type ComparisonLoader = (mapId: string, a: string, b: string, signal: AbortSignal) => Promise<PairMeasurement>;

export const loadComparison: ComparisonLoader = async (mapId, a, b, signal) => {
  const query = new URLSearchParams({ a, b });
  const pair = await request<PairMeasurement>(`/api/maps/${encodeURIComponent(mapId)}/compare?${query}`, signal);
  if (pair.galaxy_a_id !== a || pair.galaxy_b_id !== b || pair.angular_separation.unit !== "deg" ||
      [pair.distance_from_us_a, pair.distance_from_us_b, pair.estimated_3d_separation].some(
        (d) => d.unit !== "ly" || d.convention !== "comoving" ||
          (d.value !== null && (!Number.isFinite(d.value) || d.value < 0))))
    throw new Error("The comparison response is invalid. Please retry.");
  return pair;
};
