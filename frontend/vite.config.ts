import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const BACKEND = 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      // Gate 10 REST surface.
      '/api': { target: BACKEND, changeOrigin: true },
      // Unified dashboard socket. ws:true is required or the upgrade 404s.
      '/ws': { target: BACKEND, changeOrigin: true, ws: true },
      // Spec §12 surface, kept for the audio ingress socket.
      '/v1': { target: BACKEND, changeOrigin: true, ws: true },
      '/health': { target: BACKEND, changeOrigin: true },
    },
  },
});
