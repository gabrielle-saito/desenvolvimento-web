import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // No Docker em Windows/WSL2 e macOS, o aviso de "arquivo mudou" não
    // atravessa o bind mount: o polling garante o recarregamento automático.
    watch: { usePolling: process.env.VITE_POLLING === "true" },
  },
});
