import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api -> FastAPI (cổng 8000) để tránh lỗi CORS khi dev.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const proxy = {
    "/api": {
      target: env.VITE_API_TARGET || "http://127.0.0.1:8000",
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ""),
    },
  };
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy,
    },
    // `npm start` (prod): nghe mọi interface, cổng lấy từ PORT nếu nền tảng deploy cấp.
    preview: { proxy, host: true, port: Number(process.env.PORT) || 4173, strictPort: true },
  };
});
