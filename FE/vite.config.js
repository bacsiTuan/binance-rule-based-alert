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
  // Tên miền được phép truy cập (vd. host EC2), cách nhau bởi dấu phẩy; "*" = cho phép mọi host.
  const hosts = (env.VITE_ALLOWED_HOSTS || "").split(",").map((h) => h.trim()).filter(Boolean);
  const allowedHosts = hosts.includes("*") ? true : hosts;
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy,
      allowedHosts,
    },
    // `npm start` (prod): nghe mọi interface, cổng lấy từ PORT nếu nền tảng deploy cấp.
    preview: {
      proxy, allowedHosts, host: true, port: Number(process.env.PORT) || 5173, strictPort: true,
    },
  };
});
