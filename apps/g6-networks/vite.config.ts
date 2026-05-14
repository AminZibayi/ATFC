import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: __dirname,
  resolve: {
    alias: {
      '@data': resolve(__dirname, '../../data/outputs/g6-networks')
    }
  },
  build: {
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        institutional: resolve(__dirname, 'pages/institutional.html'),
        funding: resolve(__dirname, 'pages/funding.html'),
        journal: resolve(__dirname, 'pages/journal.html'),
        author_keywords: resolve(__dirname, 'pages/author_keywords.html'),
        wos_categories: resolve(__dirname, 'pages/wos_categories.html'),
      },
    },
  },
});
