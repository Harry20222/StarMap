import { expect, test, type Page } from "@playwright/test";
import measurements from "../../results/measurements.json" with { type: "json" };
import original from "../../results/prototype1_measurements.json" with { type: "json" };
import markers from "../../results/markers.json" with { type: "json" };
import {
  formatDistance,
  getComparison,
  joinGalaxyData,
  loadGalaxyField,
  type SelectableGalaxy,
} from "../src/data/galaxies";
import { layoutMarkers, markerPriority } from "../src/data/markerLayout";

const A = "goods-s-mediumjwst1180:208134";
const B = "goods-s-deephst:10008071";
const byId = new Map(measurements.galaxies.map((g) => [g.galaxy_id, g]));
async function visibleIds(page: Page) {
  return page
    .locator(".galaxy-marker")
    .evaluateAll((nodes) =>
      nodes.map((n) => n.getAttribute("data-galaxy-id")!),
    );
}
async function center(page: Page, id: string) {
  const target = page
    .getByRole("button", { name: `Select galaxy ${id}`, exact: true })
    .locator(".marker-hit");
  await target.scrollIntoViewIfNeeded();
  const bounds = await target.boundingBox();
  expect(bounds).not.toBeNull();
  return {
    x: bounds!.x + bounds!.width / 2,
    y: bounds!.y + bounds!.height / 2,
  };
}
async function activate(page: Page, id: string, mobile: boolean) {
  const point = await center(page, id);
  if (mobile) await page.touchscreen.tap(point.x, point.y);
  else await page.mouse.click(point.x, point.y);
}
async function assertPair(
  page: Page,
  a: string,
  b: string,
  pairs = measurements.pairs,
) {
  const expected = pairs.find(
    (p) =>
      [p.galaxy_a_id, p.galaxy_b_id].includes(a) &&
      [p.galaxy_a_id, p.galaxy_b_id].includes(b),
  )!;
  const sameOrder = expected.galaxy_a_id === a;
  const panel = page.getByRole("region", {
    name: "Galaxy comparison",
    exact: true,
  });
  await expect(panel.getByTestId("comparison-a")).toHaveText(a);
  await expect(panel.getByTestId("comparison-b")).toHaveText(b);
  await expect(panel.getByTestId("comparison-angle")).toHaveAttribute(
    "data-value",
    expected.angular_separation.value.toString(),
  );
  await expect(panel.getByTestId("comparison-distance-a")).toHaveAttribute(
    "data-value",
    (sameOrder
      ? expected.distance_from_us_a
      : expected.distance_from_us_b
    ).value.toString(),
  );
  await expect(panel.getByTestId("comparison-distance-b")).toHaveAttribute(
    "data-value",
    (sameOrder
      ? expected.distance_from_us_b
      : expected.distance_from_us_a
    ).value.toString(),
  );
  await expect(panel.getByTestId("comparison-3d")).toHaveAttribute(
    "data-value",
    expected.estimated_3d_separation.value.toString(),
  );
  await expect(page.getByTestId("comparison-line")).toHaveCount(1);
}

test("inspect all visible galaxies; hidden records remain in the catalog", async ({
  page,
  isMobile,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Explore GOODS-S." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Color", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const ids = await visibleIds(page);
  expect(ids.length).toBeGreaterThan(15);
  expect(ids.length).toBeLessThan(measurements.galaxies.length);
  await expect(page.getByTestId("visible-count")).toHaveText(
    `${ids.length} visible of ${measurements.galaxies.length} galaxies`,
  );
  for (const id of ids) {
    const galaxy = byId.get(id)!;
    expect(galaxy.redshift_quality).toBe("A");
    await activate(page, id, isMobile);
    const popup = page.getByRole("dialog");
    await expect(popup.getByTestId("galaxy-id")).toHaveText(id);
    await expect(popup.getByTestId("distance")).toHaveAttribute(
      "data-distance-ly",
      galaxy.distance_from_us.value.toString(),
    );
    await expect(popup.getByTestId("distance")).toHaveText(
      formatDistance(galaxy.distance_from_us),
    );
    await expect(popup.getByTestId("ra")).toHaveText(
      `${galaxy.ra_deg.toFixed(6)}°`,
    );
    await expect(popup.getByTestId("dec")).toHaveText(
      `${galaxy.dec_deg.toFixed(6)}°`,
    );
    await expect(popup.getByTestId("redshift")).toHaveText(
      galaxy.redshift.toFixed(6),
    );
    await expect(popup.getByTestId("redshift-uncertainty")).toHaveText(
      "not published",
    );
  }
  await page
    .getByRole("button", { name: "Black and white", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(await visibleIds(page)).toEqual(ids);
  await page.getByRole("button", { name: "Close galaxy details" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("same non-original pair works by desktop drag and mobile taps", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  if (isMobile) {
    await activate(page, A, true);
    await activate(page, B, true);
  } else {
    await page.getByTestId("galaxy-map").scrollIntoViewIfNeeded();
    const from = await center(page, A);
    const to = await center(page, B);
    await page.mouse.move(from.x, from.y);
    await page.mouse.down();
    await page.mouse.move(to.x, to.y, { steps: 12 });
    await expect(page.getByTestId("comparison-line")).toBeVisible();
    await page.mouse.up();
  }
  await assertPair(page, A, B);
  await page
    .getByRole("button", { name: "Black and white", exact: true })
    .click();
  await assertPair(page, A, B);
  await page
    .getByRole("button", { name: "Clear comparison", exact: true })
    .click();
  await expect(page.getByTestId("comparison-line")).toHaveCount(0);
});

test("keyboard pair selection, reversed A/B distances, and Escape", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  const first = page.getByRole("button", {
    name: `Select galaxy ${B}`,
    exact: true,
  });
  const second = page.getByRole("button", {
    name: `Select galaxy ${A}`,
    exact: true,
  });
  await first.focus();
  await page.keyboard.press("Enter");
  await second.focus();
  await page.keyboard.press("Space");
  await assertPair(page, B, A);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("comparison-line")).toHaveCount(0);
  await expect(page.getByTestId("comparison-a")).toHaveCount(0);
});

test("drag to empty sky or starting circle cancels unfinished comparison", async ({
  page,
  isMobile,
}) => {
  test.skip(
    isMobile,
    "Desktop pointer-drag cancellation; mobile sequential cancellation is checked separately.",
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByTestId("galaxy-map").scrollIntoViewIfNeeded();
  let from = await center(page, A);
  const image = await page.getByTestId("galaxy-map").boundingBox();
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(image!.x + 10, image!.y + 10, { steps: 10 });
  await page.mouse.up();
  await expect(page.getByTestId("comparison-line")).toHaveCount(0);
  await expect(page.getByTestId("comparison-a")).toHaveCount(0);
  from = await center(page, A);
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x + 40, from.y, { steps: 4 });
  await page.mouse.move(from.x, from.y, { steps: 4 });
  await page.mouse.up();
  await expect(page.getByTestId("comparison-line")).toHaveCount(0);
  await expect(page.getByTestId("comparison-a")).toHaveCount(0);
});

test("selecting the starting galaxy twice cancels a pending pair", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await activate(page, A, isMobile);
  await activate(page, A, isMobile);
  await expect(page.getByTestId("comparison-a")).toHaveCount(0);
  await expect(page.getByRole("status")).toContainText(
    "Drag between two rings",
  );
});

test("all visible circles remain aligned and non-overlapping through resize", async ({
  page,
}) => {
  await page.goto("/");
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1100 });
    await page.getByTestId("galaxy-map").scrollIntoViewIfNeeded();
    await page.waitForFunction(() => {
      const svg = document.querySelector(".galaxy-map") as SVGSVGElement;
      const node = svg?.querySelector(".marker-ring") as SVGCircleElement;
      return (
        !!node &&
        (node.r.baseVal.value * svg.getBoundingClientRect().width) / 2000 >= 5.9
      );
    });
    const positions = await page
      .locator(".galaxy-marker")
      .evaluateAll((nodes) =>
        nodes.map((node) => {
          const n = node as SVGGraphicsElement;
          const matrix = n.getScreenCTM()!;
          const center = new DOMPoint(0, 0).matrixTransform(matrix);
          const ring = n.querySelector(".marker-ring") as SVGCircleElement;
          const selected = n.querySelector(
            ".marker-selection",
          ) as SVGCircleElement | null;
          const r =
            Math.max(ring.r.baseVal.value, selected?.r.baseVal.value ?? 0) *
            Math.hypot(matrix.a, matrix.b);
          const image = n
            .ownerSVGElement!.querySelector("image")!
            .getBoundingClientRect();
          return {
            id: n.getAttribute("data-galaxy-id")!,
            x: center.x,
            y: center.y,
            r,
            nx: (center.x - image.x) / image.width,
            ny: (center.y - image.y) / image.height,
          };
        }),
      );
    for (const [i, p] of positions.entries()) {
      const marker = markers.markers.find((m) => m.galaxy_id === p.id)!;
      expect(p.nx).toBeCloseTo((marker.x + 0.5) / markers.shape_yx[1], 6);
      expect(p.ny).toBeCloseTo(
        (markers.shape_yx[0] - 0.5 - marker.y) / markers.shape_yx[0],
        6,
      );
      for (const q of positions.slice(i + 1))
        expect(Math.hypot(p.x - q.x, p.y - q.y)).toBeGreaterThan(p.r + q.r + 1);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});

test("hover, focus and mobile tap show plain-language scientific definitions", async ({
  page,
  isMobile,
}) => {
  await page.goto("/");
  await activate(page, B, isMobile);
  const popup = page.getByRole("dialog");
  for (const term of [
    "Right ascension",
    "Declination",
    "Spectroscopic redshift",
    "Redshift quality",
    "Redshift uncertainty",
    "Comoving distance",
    "Light-year",
  ]) {
    await expect(
      popup.getByRole("button", { name: `About ${term}`, exact: true }),
    ).toBeVisible();
  }
  const help = popup.getByRole("button", {
    name: "About Redshift quality",
    exact: true,
  });
  if (isMobile) await help.tap();
  else await help.hover();
  await expect(page.getByRole("tooltip")).toContainText(
    "does not give a numerical error margin",
  );
  const bounds = await page.getByRole("tooltip").boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  await expect(popup).toBeVisible();
  await page.keyboard.press("Tab");
  await help.focus();
  await expect(page.getByRole("tooltip")).toBeVisible();
  await page.getByRole("heading", { name: "Explore GOODS-S." }).click();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
});

test("original 15 have 105 pairs; expanded catalog supports every pair and reverse order", () => {
  const field = loadGalaxyField();
  expect(field.galaxies.length).toBe(43);
  expect(field.comparisons.size).toBe(903);
  const ids = new Set(original.galaxies.map((g) => g.galaxy_id));
  const initial = joinGalaxyData(
    {
      ...markers,
      markers: markers.markers.filter((m) => ids.has(m.galaxy_id)),
    },
    original,
  );
  expect(initial.galaxies.length).toBe(15);
  expect(initial.comparisons.size).toBe(105);
  for (const pair of original.pairs) {
    const reversed = getComparison(initial, pair.galaxy_b_id, pair.galaxy_a_id);
    expect(reversed.angular_separation).toEqual(pair.angular_separation);
    expect(reversed.estimated_3d_separation).toEqual(
      pair.estimated_3d_separation,
    );
    expect(reversed.distance_from_us_a).toEqual(pair.distance_from_us_b);
  }
});

test("collision priority uses quality, then comparable size, then stable ID", () => {
  const base = loadGalaxyField().galaxies[0];
  const mk = (
    id: string,
    size: number | null,
    quality = "A",
  ): SelectableGalaxy => ({
    ...base,
    galaxy_id: id,
    x: 100,
    y: 100,
    redshift_quality: quality,
    apparent_size_arcsec: size,
    apparent_size_measurement: size === null ? null : "same metric",
  });
  expect(
    layoutMarkers([mk("small-a", 0.1), mk("large-z", 0.4)], 2000, 350)
      .visible[0].galaxy_id,
  ).toBe("large-z");
  expect(
    layoutMarkers([mk("quality-b", 10, "B"), mk("quality-a", 0.1)], 2000, 350)
      .visible[0].galaxy_id,
  ).toBe("quality-a");
  expect(
    layoutMarkers([mk("z", null), mk("a", 0.4)], 2000, 350).visible[0]
      .galaxy_id,
  ).toBe("a");
  const galaxies = loadGalaxyField().galaxies;
  for (const width of [983, 352, 282]) {
    const layout = layoutMarkers(galaxies, 2000, width);
    const visible = new Set(layout.visible.map((g) => g.galaxy_id));
    for (const hidden of galaxies.filter((g) => !visible.has(g.galaxy_id))) {
      expect(
        layout.visible.some(
          (g) =>
            Math.hypot(g.x - hidden.x, g.y - hidden.y) < layout.clearance &&
            markerPriority(g, hidden) <= 0,
        ),
      ).toBe(true);
    }
    expect(
      layoutMarkers([...galaxies].reverse(), 2000, width)
        .visible.map((g) => g.galaxy_id)
        .sort(),
    ).toEqual([...visible].sort());
  }
});

test("the same comparison UI works with the initial 15-galaxy / 105-pair fixture", async ({
  page,
  isMobile,
}) => {
  await page.goto("/tests/fixtures/prototype1.html");
  await expect(page.getByTestId("visible-count")).toContainText(
    "of 15 galaxies",
  );
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await activate(page, "goods-s-deephst:17160", isMobile);
  await activate(page, B, isMobile);
  await assertPair(page, "goods-s-deephst:17160", B, original.pairs);
});

test("resizing keeps selected galaxies visible even when normal culling would hide them", async ({
  page,
  isMobile,
}) => {
  test.skip(
    isMobile,
    "One desktop-to-mobile resize transition covers this state change.",
  );
  await page.goto("/");
  const large = await visibleIds(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("visible-count")).not.toContainText(
    `${large.length} visible`,
  );
  const small = await visibleIds(page);
  const disappearing = large.find((id) => !small.includes(id))!;
  const remaining = small[0];
  expect(disappearing).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page
    .getByRole("button", { name: `Select galaxy ${disappearing}`, exact: true })
    .press("Enter");
  await page
    .getByRole("button", { name: `Select galaxy ${remaining}`, exact: true })
    .press("Enter");
  await assertPair(page, disappearing, remaining);
  await page.setViewportSize({ width: 390, height: 844 });
  await assertPair(page, disappearing, remaining);
  await expect(
    page.locator(`[data-galaxy-id="${disappearing}"].is-selected`),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Clear comparison", exact: true })
    .click();
  await expect(page.locator(`[data-galaxy-id="${disappearing}"]`)).toHaveCount(
    0,
  );
});

test("resizing preserves a comparison when both endpoints stay visible", async ({
  page,
  isMobile,
}) => {
  test.skip(
    isMobile,
    "One desktop-to-mobile resize transition covers this state change.",
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page
    .getByRole("button", { name: `Select galaxy ${A}`, exact: true })
    .press("Enter");
  await page
    .getByRole("button", { name: `Select galaxy ${B}`, exact: true })
    .press("Enter");
  await assertPair(page, A, B);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("visible-count")).toContainText("28 visible");
  await assertPair(page, A, B);
  await page.setViewportSize({ width: 1440, height: 1100 });
  await expect(page.getByTestId("visible-count")).toContainText("39 visible");
  await assertPair(page, A, B);
});
