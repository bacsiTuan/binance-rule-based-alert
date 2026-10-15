// Server only: never import this module from src/ or expose the key through VITE_*.
export function createTelegramTestMiddleware({ enabled, key }) {
  return (req, res, next) => {
    if (!["/api/ai/telegram-test", "/api/telegram/trigger"].includes(req.url?.split("?")[0])) return next();
    const reject = (status, detail) => {
      res.statusCode = status;
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Cache-Control", "no-store");
      res.end(JSON.stringify({ detail }));
    };
    // This proxy can authorize a real send, so only the local dashboard may use it.
    // Check both socket and Origin/Host; neither CORS nor a hidden button is authorization.
    let localOrigin = false;
    try {
      const origin = new URL(req.headers.origin);
      localOrigin = ["http:", "https:"].includes(origin.protocol)
        && ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname)
        && origin.host === req.headers.host;
    } catch { /* Missing or malformed origin is not a dashboard request. */ }
    const localSocket = ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(req.socket.remoteAddress);
    if (!localOrigin || !localSocket || req.method !== "POST"
        || req.headers["content-type"]?.split(";")[0].trim().toLowerCase() !== "application/json") {
      return reject(403, "telegram_test_local_only");
    }
    if (!enabled || !key || key.length < 24 || key.length > 256) {
      return reject(503, "telegram_test_proxy_unconfigured");
    }
    req.headers["x-telegram-test-key"] = key;
    next();
  };
}
