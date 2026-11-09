import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const python = process.env.STARMAP_TEST_PYTHON ?? (existsSync("../my_venv/Scripts/python.exe")
  ? "../my_venv/Scripts/python.exe" : "python");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure" },
  projects: [
    {
      name: "desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1100 } },
    },
    {
      name: "mobile",
      use: {
        browserName: "chromium",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: [{
    command: `"${python}" tests/serve_api.py`,
    url: "http://127.0.0.1:8001/api/health",
    reuseExistingServer: false,
  }, {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: false,
    env: { STARMAP_API_PROXY: "http://127.0.0.1:8001" },
  }],
});
