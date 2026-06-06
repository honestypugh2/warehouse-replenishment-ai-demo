import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend runs on :8080. The dev server proxies /api -> backend so the
// frontend can call the FastAPI demo endpoints without CORS friction.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
