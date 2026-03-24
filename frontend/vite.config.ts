import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

const srcDir = fileURLToPath(new URL("./src", import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const port = Number(env.VITE_PORT) || 5173;
  const host = env.VITE_HOST || "0.0.0.0";
  /** Where to forward `/api` in dev (local Flask or remote). Not `VITE_API_BASE_URL` — that is for built SPA → API. */
  const proxyTarget =
    env.VITE_DEV_PROXY_TARGET || env.VITE_API_PROXY || "http://127.0.0.1:5001";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": srcDir,
      },
    },
    server: {
      host,
      port,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
  };
});
