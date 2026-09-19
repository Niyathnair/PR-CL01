import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Backend runs on 8000; the frontend talks to it under /v1.
      "/v1": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
