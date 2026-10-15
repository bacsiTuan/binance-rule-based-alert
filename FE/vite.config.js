import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { createTelegramTestMiddleware } from "./server/telegramTestProxy.js";

// Proxy /api -> FastAPI (cổng 8000) để tránh lỗi CORS khi dev.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, fileURLToPath(new URL(".", import.meta.url)), "VITE_");
  // Read only diagnostic settings from the shared backend .env, on the Node server.
  const testEnv = loadEnv(mode, fileURLToPath(new URL("..", import.meta.url)), "TELEGRAM_TEST_");
  const middleware = createTelegramTestMiddleware({
    enabled: /^(true|1|yes|on)$/i.test(testEnv.TELEGRAM_TEST_ENABLED || "false"),
    key: testEnv.TELEGRAM_TEST_KEY,
  });
  const testProxy = {
    name: "local-telegram-test-auth",
    configureServer: (server) => { server.middlewares.use(middleware); },
    configurePreviewServer: (server) => { server.middlewares.use(middleware); },
  };
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
    plugins: [react(), testProxy],
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
