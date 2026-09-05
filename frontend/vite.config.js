import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, `npm run dev` runs Vite on :5173 and proxies /api to the Flask
// server on :5000, so the frontend code can always call relative /api/...
// paths -- no environment-specific base URL branching needed. In a
// production build, Flask serves this app's static files directly from
// the same origin, so the same relative paths just work with no proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
