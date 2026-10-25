import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    // 공통 UI(apps/shared/titlebar.js·menus.json·maps-theme.css)를 루트 밖에서 불러온다
    fs: { allow: [".", "../shared"] }
  },
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-three": ["three"],
          "vendor-r3f": ["@react-three/fiber"],
          "vendor-lucide": ["lucide-react"],
          "vendor-xlsx": ["xlsx"]
        }
      }
    }
  }
});
