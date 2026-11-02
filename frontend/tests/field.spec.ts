import { expect, test } from "@playwright/test";
import measurements from "../../results/measurements.json" with { type: "json" };
import markers from "../../results/markers.json" with { type: "json" };
import { formatDistance, joinGalaxyData } from "../src/data/galaxies";

const selectable = measurements.galaxies.filter(
  (galaxy) => galaxy.redshift_quality === "A",
);

test("all quality-A galaxies are selectable and show their matching export data", async ({
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
    page.getByRole("button", { name: /^Select galaxy / }),
  ).toHaveCount(selectable.length);
  await expect(
    page.getByText(`${selectable.length} selectable galaxies`),
  ).toBeVisible();
  await expect(
    page.getByText(
      "GOODS-S · F090W (blue) + F200W (green) + F444W (red) color image (JADES DR2) · galaxy catalog (JADES DR3).",
    ),
  ).toBeVisible();

  for (const galaxy of selectable) {
    const marker = page.getByRole("button", {
      name: `Select galaxy ${galaxy.galaxy_id}`,
      exact: true,
    });
    const hitTarget = marker.locator(".marker-hit");
    if (isMobile) {
      // Simulate a finger at the visible ring center. Overlapping enlarged hit
      // areas deliberately delegate to the nearest center, regardless of which
      // SVG circle receives the event.
      await hitTarget.scrollIntoViewIfNeeded();
      const bounds = await hitTarget.boundingBox();
      expect(bounds).not.toBeNull();
      await page.touchscreen.tap(
        bounds!.x + bounds!.width / 2,
        bounds!.y + bounds!.height / 2,
      );
    } else await hitTarget.click();
    const popup = page.getByRole("dialog");
    await expect(popup).toBeVisible();
    await expect(popup.getByTestId("galaxy-id")).toHaveText(galaxy.galaxy_id);
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
    await expect(
      popup.getByText(`${measurements.cosmology.name} cosmological model`),
    ).toBeVisible();
    await expect(marker).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".galaxy-marker.is-selected")).toHaveCount(1);
  }
  await page.getByRole("button", { name: "Close galaxy details" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".galaxy-marker.is-selected")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("keyboard selection, Escape dismissal, and focus restoration", async ({
  page,
}) => {
  await page.goto("/");
  const galaxy = selectable[0];
  const marker = page.getByRole("button", {
    name: `Select galaxy ${galaxy.galaxy_id}`,
    exact: true,
  });
  await marker.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(marker).toBeFocused();
  await page.keyboard.press("Space");
  await expect(page.getByTestId("galaxy-id")).toHaveText(galaxy.galaxy_id);
});

test("native image and every marker share their transformed coordinates as the map resizes", async ({
  page,
}) => {
  await page.goto("/");
  const svg = page.getByTestId("galaxy-map");
  await expect(svg).toBeVisible();
  const image = svg.locator("image");
  const loadedImage = await image.evaluate(async (element) => {
    const bitmap = new Image();
    bitmap.src = element.getAttribute("href")!;
    await bitmap.decode();
    return { width: bitmap.naturalWidth, height: bitmap.naturalHeight };
  });
  expect(loadedImage).toEqual({
    width: markers.shape_yx[1],
    height: markers.shape_yx[0],
  });
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(svg).toHaveAttribute(
      "viewBox",
      `-0.5 -0.5 ${markers.shape_yx[1]} ${markers.shape_yx[0]}`,
    );
    for (const marker of markers.markers) {
      const element = page.getByRole("button", {
        name: `Select galaxy ${marker.galaxy_id}`,
        exact: true,
      });
      await expect(element).toHaveAttribute(
        "transform",
        `translate(${marker.x} ${markers.shape_yx[0] - 1 - marker.y})`,
      );
      const location = await element.evaluate((node) => {
        const center = new DOMPoint(0, 0).matrixTransform(
          (node as SVGGraphicsElement).getScreenCTM()!,
        );
        const image = (
          node as SVGGraphicsElement
        ).ownerSVGElement!.querySelector("image")!;
        const imageRect = image.getBoundingClientRect();
        return {
          x: (center.x - imageRect.x) / imageRect.width,
          y: (center.y - imageRect.y) / imageRect.height,
        };
      });
      expect(location.x).toBeCloseTo((marker.x + 0.5) / markers.shape_yx[1], 6);
      expect(location.y).toBeCloseTo(
        (markers.shape_yx[0] - 0.5 - marker.y) / markers.shape_yx[0],
        6,
      );
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});

test("join uses IDs and quality, independent of JSON order or sample size", () => {
  const subset = {
    ...measurements,
    galaxies: [...measurements.galaxies].reverse().map((g, i) => ({
      ...g,
      redshift_quality: i === 0 ? "B" : g.redshift_quality,
    })),
  };
  const field = joinGalaxyData(markers, subset);
  expect(field.galaxies.length).toBe(selectable.length - 1);
  expect(field.galaxies[0].galaxy_id).toBe(markers.markers[0].galaxy_id);
  expect(field.galaxies[0].distance_from_us).toEqual(
    measurements.galaxies[0].distance_from_us,
  );
  expect(() =>
    joinGalaxyData(
      {
        ...markers,
        markers: [{ ...markers.markers[0], galaxy_id: "missing" }],
      },
      measurements,
    ),
  ).toThrow("do not match");
  expect(() =>
    joinGalaxyData(
      { ...markers, markers: [markers.markers[0], markers.markers[0]] },
      measurements,
    ),
  ).toThrow("duplicate");
});
