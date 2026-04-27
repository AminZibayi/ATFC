import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    outDir: '../../plots/g6_networks',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        institutional: resolve(__dirname, 'pages/institutional.html'),
        funding: resolve(__dirname, 'pages/funding.html'),
        journal: resolve(__dirname, 'pages/journal.html'),
      },
    },
  },
});
