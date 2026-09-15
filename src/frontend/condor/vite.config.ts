import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import * as path from "node:path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    fs: {
      // Allows Vite to crawl outside of the condor/ folder to compile the grid plugin
      allow: [".."],
    },
    proxy: {
      // Any frontend request starting with '/api' will bypass CORS
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  resolve: {
    alias: {
      // Creates a bulletproof module fallback path map
      "react-leaflet-mgrs-graticule": path.resolve(
        __dirname,
        "../React-Leaflet-MGRS-Graticule/src/index.ts",
      ),
    },
  },
});
