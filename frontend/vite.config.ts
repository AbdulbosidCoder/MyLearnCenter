import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // During development the API runs separately on :8000.
    proxy: { "/api": "http://localhost:8000" },
    // Vite rejects requests from unknown hosts; allow Cloudflare quick-tunnel addresses.
    allowedHosts: [".trycloudflare.com"],
  },
});
