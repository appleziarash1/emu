import { defineConfig } from 'vite';

// `base` is overridable so the same build can be served from a domain root
// (local preview, custom host) or from a GitHub Pages project subpath
// (/veilborn/) without editing assets.
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  build: {
    target: 'es2020',
    // Phaser is ~1.3MB; splitting it means the game code can be re-downloaded
    // on its own after an update instead of busting the whole bundle, which
    // matters on a phone connection.
    rollupOptions: {
      output: {
        manualChunks: {
          phaser: ['phaser'],
        },
      },
    },
    chunkSizeWarningLimit: 1600,
    sourcemap: false,
  },
  server: {
    host: true,
  },
});
