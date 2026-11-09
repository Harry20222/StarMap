import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  preview: {
    proxy: { "/api": { target: process.env.STARMAP_API_PROXY ?? "http://127.0.0.1:8000", changeOrigin: true } },
  },
  server: {
    fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] },
    proxy: { "/api": { target: process.env.STARMAP_API_PROXY ?? "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
