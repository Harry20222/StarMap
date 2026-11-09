import { expect, test, type Page } from "@playwright/test";
import measurements from "../../results/measurements.json" with { type: "json" };
import markers from "../../results/markers.json" with { type: "json" };
import { expectMeasurement } from "./measurement";

const exampleA = "goods-s-deephst:21598";
const exampleB = "goods-s-deephst:21842";
const mapA = "goods-s-mediumjwst1180:208134";
const marker = (page: Page, id: string) =>
  page.locator(`[data-galaxy-id="${id}"]`);

async function ids(page: Page) {
  await expect(page.locator(".galaxy-marker").first()).toBeVisible();
  return page
    .locator(".galaxy-marker")
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("data-galaxy-id")));
}
async function searchPick(page: Page, id: string, touch = false) {
  await page.getByRole("combobox", { name: "Find a galaxy" }).fill(id);
  const option = page.getByRole("option", { name: id, exact: true });
  if (touch) await option.tap();
  else await option.click();
}
async function aligned(page: Page, id: string) {
  const center = await marker(page, id).evaluate((node) => {
    const n = node as SVGGraphicsElement;
    const p = new DOMPoint(0, 0).matrixTransform(n.getScreenCTM()!);
    const image = n
      .ownerSVGElement!.querySelector("image")!
      .getBoundingClientRect();
    return {
      x: (p.x - image.x) / image.width,
      y: (p.y - image.y) / image.height,
    };
  });
  const source = markers.markers.find((g) => g.galaxy_id === id)!;
  expect(center.x).toBeCloseTo((source.x + 0.5) / 2000, 6);
  expect(center.y).toBeCloseTo((1999.5 - source.y) / 2000, 6);
}
async function pair(page: Page, a: string, b: string) {
  const expected = measurements.pairs.find(
    (p) =>
      [p.galaxy_a_id, p.galaxy_b_id].includes(a) &&
      [p.galaxy_a_id, p.galaxy_b_id].includes(b),
  )!;
  const direct = expected.galaxy_a_id === a;
  await expect(page.getByTestId("comparison-a")).toHaveText(a);
  await expect(page.getByTestId("comparison-b")).toHaveText(b);
  for (const [name, value] of [
    ["angle", expected.angular_separation.value],
    [
      "distance-a",
      (direct ? expected.distance_from_us_a : expected.distance_from_us_b)
        .value,
    ],
    [
      "distance-b",
      (direct ? expected.distance_from_us_b : expected.distance_from_us_a)
        .value,
    ],
    ["3d", expected.estimated_3d_separation.value],
  ] as const)
    await expectMeasurement(page.getByTestId(`comparison-${name}`), value);
  await expect(page.getByTestId("comparison-line")).toHaveCount(1);
  for (const id of [a, b]) {
    await expect(marker(page, id)).toHaveClass(/is-selected/);
    await aligned(page, id);
  }
}

test("search lists every galaxy and inspects all normally hidden galaxies", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  const visible = await ids(page);
  const hidden = measurements.galaxies.filter(
    (g) => !visible.includes(g.galaxy_id),
  );
  expect(hidden.length).toBeGreaterThan(0);
  const search = page.getByRole("combobox", { name: "Find a galaxy" });
  await search.focus();
  await expect(page.getByRole("option")).toHaveCount(
    measurements.galaxies.length,
  );
  for (const g of hidden) {
    await searchPick(page, g.galaxy_id, isMobile);
    await expect(page.getByTestId("galaxy-id")).toHaveText(g.galaxy_id);
    await expect(page.getByTestId("distance")).toHaveAttribute(
      "data-distance-ly",
      String(g.distance_from_us.value),
    );
    await expect(marker(page, g.galaxy_id)).toHaveClass(/is-selected/);
    await aligned(page, g.galaxy_id);
    await page.getByRole("button", { name: "Inspect", exact: true }).click();
    await expect(page.getByTestId("galaxy-id")).toHaveText(g.galaxy_id);
  }
  await search.fill("no-such-galaxy");
  await expect(page.getByRole("option")).toHaveCount(0);
  await expect(page.getByText("No galaxies match this ID.")).toBeVisible();
  await search.press("Escape");
  await expect(search).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("search keyboard navigation, selection, dismissal and focus return", async ({
  page,
}) => {
  await page.goto("/");
  const visible = await ids(page);
  const hidden = measurements.galaxies.find(
    (g) => !visible.includes(g.galaxy_id),
  )!;
  const search = page.getByRole("combobox", { name: "Find a galaxy" });
  await search.focus();
  await search.press("ArrowDown");
  await expect(page.getByRole("option").first()).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await search.press("End");
  await expect(page.getByRole("option").last()).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await search.press("Home");
  await search.press("ArrowUp");
  await expect(page.getByRole("option").last()).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await search.fill(hidden.galaxy_id);
  await search.press("Enter");
  await expect(page.getByTestId("galaxy-id")).toHaveText(hidden.galaxy_id);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(search).toBeFocused();
});

test("map and search can form a pair; active Compare preserves pending and complete selections", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  const visible = await ids(page);
  const hidden = measurements.galaxies.find(
    (g) => !visible.includes(g.galaxy_id),
  )!.galaxy_id;
  const compare = page.getByRole("button", { name: "Compare", exact: true });
  await compare.click();
  const start = marker(page, mapA).locator(".marker-hit");
  if (isMobile) await start.tap();
  else await start.click();
  await compare.click();
  await expect(
    page.getByRole("region", { name: "Galaxy comparison", exact: true }),
  ).toContainText(`A · ${mapA}`);
  await searchPick(page, hidden, isMobile);
  await pair(page, mapA, hidden);
  await compare.click();
  await pair(page, mapA, hidden);
  for (const name of ["Black and white", "Color"]) {
    await page.getByRole("button", { name, exact: true }).click();
    await pair(page, mapA, hidden);
  }
  await page.getByRole("button", { name: "Inspect", exact: true }).click();
  await expect(page.getByTestId("comparison-line")).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("both search selections and the example button use the exported comparison", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await searchPick(page, exampleA, isMobile);
  await searchPick(page, exampleB, isMobile);
  await pair(page, exampleA, exampleB);
  if (isMobile)
    await expect(page.locator(".selected-overlap-note")).toBeVisible();
  await page
    .getByRole("button", { name: "Clear comparison", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Try an example pair", exact: true })
    .click();
  await pair(page, exampleA, exampleB);
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await pair(page, exampleA, exampleB);
  for (const name of ["Black and white", "Color"]) {
    await page.getByRole("button", { name, exact: true }).click();
    await pair(page, exampleA, exampleB);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await pair(page, exampleA, exampleB);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("responsive WebP image loads alone; grayscale waits for its toggle", async ({
  page,
  isMobile,
}) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (
      request.resourceType() === "image" &&
      request.url().includes("goods_s_")
    )
      requests.push(request.url());
  });
  await page.goto("/");
  const width = isMobile ? 640 : 1280;
  await expect(page.locator(".galaxy-map image")).toHaveAttribute(
    "data-image-width",
    String(width),
  );
  await expect.poll(() => requests.length).toBe(1);
  expect(requests[0]).toContain(`goods_s_color-${width}`);
  expect(requests[0]).toContain(".webp");
  expect(
    requests.some((url) => url.includes("f200w") || url.includes(".png")),
  ).toBe(false);
  await page
    .getByRole("button", { name: "Black and white", exact: true })
    .click();
  await expect
    .poll(() => requests.some((url) => url.includes(`goods_s_f200w-${width}`)))
    .toBe(true);
  await aligned(page, mapA);
});

test("a high-density phone requests one appropriately sized color image", async ({
  browser,
  isMobile,
}) => {
  test.skip(isMobile, "One high-density mobile context covers both projects.");
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 3,
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.resourceType() === "image" && r.url().includes("goods_s_"))
      requests.push(r.url());
  });
  try {
    await page.goto("http://127.0.0.1:5173/");
    await expect(page.locator(".galaxy-map image")).toHaveAttribute(
      "data-image-width",
      "1280",
    );
    await expect.poll(() => requests.length).toBe(1);
    expect(requests[0]).toContain("goods_s_color-1280");
  } finally {
    await context.close();
  }
});
