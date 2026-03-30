import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api/gateway': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/gateway/, '/api/v1'),
      },
      '/api/computation': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/computation/, '/api/v1'),
      },
      '/api/reports': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/reports/, '/api/v1'),
      },
    },
  },
});
