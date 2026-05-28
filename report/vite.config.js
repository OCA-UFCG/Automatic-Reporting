import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    ssr: 'src/ssr-entry.jsx',
    outDir: 'ssr-dist',
    rollupOptions: {
      output: {
        format: 'es',
      },
    },
  },
});
