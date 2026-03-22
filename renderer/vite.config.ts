import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',          // 👈 THIS is the important part
  build: {
    outDir: 'dist',    // default anyway, but explicit is nice
  },
});

// vite