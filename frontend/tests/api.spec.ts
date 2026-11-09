import { expect, test, type Page } from "@playwright/test";
import measurements from "../../results/measurements.json" with { type: "json" };

const exampleA = "goods-s-deephst:21598";
const exampleB = "goods-s-deephst:21842";
const otherA = "goods-s-mediumjwst1180:208134";
const otherB = "goods-s-deephst:10008071";

async function ready(page: Page) {
  await expect(page.locator(".galaxy-marker").first()).toBeVisible();
}

async function choose(page: Page, id: string) {
  const search = page.getByRole("combobox", { name: "Find a galaxy" });
  await search.fill(id);
  await search.press("Enter");
}

test("catalog loading, database error and successful retry", async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/maps", async (route) => {
    await gate;
    await route.fulfill({ status: 503, json: { error: "unavailable" } });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Loading the field…" })).toBeVisible();
  release();
  await expect(page.getByRole("alert")).toContainText("catalog database is unavailable");
  await expect(page.locator(".galaxy-marker")).toHaveCount(0);
  await page.unroute("**/api/maps");
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await ready(page);
});

test("empty maps and empty eligible catalog have retry states", async ({ page }) => {
  await page.route("**/api/maps", (route) => route.fulfill({ json: { maps: [] } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "No galaxies are available." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
  await page.unroute("**/api/maps");
  await page.route("**/api/maps/goods-s/galaxies", (route) => route.fulfill({
    json: { map_id: "goods-s", galaxies: [], markers: [] },
  }));
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No galaxies are available." })).toBeVisible();
});

test("failed comparison retries without losing the selected galaxies", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  await page.route("**/api/maps/goods-s/compare?**", (route) => route.fulfill({ status: 503, json: { error: "unavailable" } }));
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByRole("button", { name: "Try an example pair" }).click();
  await expect(page.getByRole("alert")).toContainText("catalog database is unavailable");
  await expect(page.getByTestId("comparison-line")).toHaveCount(1);
  await page.unroute("**/api/maps/goods-s/compare?**");
  await page.getByRole("button", { name: "Retry comparison" }).click();
  await expect(page.getByTestId("comparison-a")).toHaveText(exampleA);
  await expect(page.getByTestId("comparison-b")).toHaveText(exampleB);
});

test("a delayed older comparison cannot replace the new pair or a cleared selection", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  let release!: () => void;
  let arrived!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { arrived = resolve; });
  await page.route("**/api/maps/goods-s/compare?**", async (route) => {
    const query = new URL(route.request().url()).searchParams;
    if (query.get("a") !== exampleA) return route.continue();
    arrived();
    await gate;
    const pair = measurements.pairs.find((p) => p.galaxy_a_id === exampleA && p.galaxy_b_id === exampleB)!;
    await route.fulfill({ json: pair }).catch(() => {}); // The browser may have aborted it.
  });
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByRole("button", { name: "Try an example pair" }).click();
  await requested;
  await expect(page.getByRole("heading", { name: "Calculating separation…" })).toBeVisible();
  await page.getByRole("button", { name: "Clear comparison", exact: true }).click();
  await choose(page, otherA);
  await choose(page, otherB);
  await expect(page.getByTestId("comparison-a")).toHaveText(otherA);
  release();
  await expect(page.getByTestId("comparison-b")).toHaveText(otherB);
  await page.getByRole("button", { name: "Clear comparison", exact: true }).click();
  await expect(page.getByTestId("comparison-a")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Connect two galaxies." })).toBeVisible();
});

test("unsupported pixel origins produce a recoverable error", async ({ page }) => {
  await page.route("**/api/maps/goods-s", async (route) => {
    const response = await route.fetch();
    await route.fulfill({ json: { ...await response.json(), pixel_origin: 1 } });
  });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("image coordinate information is not supported");
  await expect(page.getByRole("button", { name: "Retry", exact: true })).toBeVisible();
});
