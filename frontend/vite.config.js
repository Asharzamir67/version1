// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  define: {
    'process.env': process.env,
    'process.platform': JSON.stringify(process.platform),
    'global': 'window'  // Add this line
  },
  logLevel: 'warn', // Reduce console noise - only show warnings and errors
  esbuild: {
    logOverride: { 'this-is-undefined-in-esm': 'silent' }, // Suppress common esbuild warnings
  },
  server: {
    port: 3000,
    open: false,
    cors: true,
    strictPort: true,
    proxy: {
      '/user': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/images': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    rollupOptions: {
      external: ['electron'],  // Add this to prevent bundling electron
    }
  },
  resolve: {
    alias: {
      'electron': 'electron',
    },
  },
  optimizeDeps: {
    exclude: ['electron'],
  },
});