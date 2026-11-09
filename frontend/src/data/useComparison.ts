import { useEffect, useState } from "react";
import { loadComparison, type ComparisonLoader } from "./api";
import type { PairMeasurement } from "./galaxies";

export function useComparison(mapId: string, a: string | undefined, b: string | undefined, loader: ComparisonLoader = loadComparison) {
  const [attempt, retry] = useState(0);
  const [result, setResult] = useState<{ key: string; pair?: PairMeasurement; error?: string } | null>(null);
  const key = JSON.stringify([mapId, a, b, attempt]);
  useEffect(() => {
    if (!a || !b) return;
    const controller = new AbortController();
    let active = true;
    loader(mapId, a, b, controller.signal).then(
      (pair) => { if (active) setResult({ key, pair }); },
      (error: unknown) => { if (active) setResult({ key, error: error instanceof Error ? error.message : "The comparison could not be loaded." }); },
    );
    return () => { active = false; controller.abort(); };
  }, [mapId, a, b, loader, key]);
  const current = result?.key === key ? result : null;
  return { pair: current?.pair, error: current?.error, loading: Boolean(a && b && !current), retry: () => retry((n) => n + 1) };
}
