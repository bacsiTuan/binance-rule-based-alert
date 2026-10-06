import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api -> FastAPI (cổng 8000) để tránh lỗi CORS khi dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
