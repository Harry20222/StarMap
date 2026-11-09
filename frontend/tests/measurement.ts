import { expect, type Locator } from "@playwright/test";

// Live Astropy calculations in reversed order can differ at machine precision.
// Match the backend regression tolerance instead of comparing float strings.
export async function expectMeasurement(locator: Locator, expected: number | null) {
  if (expected === null) {
    await expect(locator).toHaveAttribute("data-value", "unknown");
    return;
  }
  await expect.poll(async () => {
    const text = await locator.getAttribute("data-value");
    if (text === null || text === "unknown") return false;
    return Math.abs(Number(text) - expected) <= Math.max(1e-12, Math.abs(expected) * 1e-10);
  }).toBe(true);
}
