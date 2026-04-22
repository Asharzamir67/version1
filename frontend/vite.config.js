// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: {
        name: 'Sealant Detection Monitor',
        short_name: 'SealantApp',
        description: 'AI-Powered Sealant Inspection System for Workers',
        theme_color: '#000000',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  base: './',
  define: {
    'process.env': {},
    'process.platform': JSON.stringify(process.platform),
    'global': 'globalThis'
  },
  logLevel: 'info', // Increased for better debugging of dev-server crashes
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
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/admin': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/images': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: 'http://localhost:8001',
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