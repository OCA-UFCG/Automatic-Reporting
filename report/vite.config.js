import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    ssr: true,
    outDir: 'ssr-dist',
    rollupOptions: {
      input: {
        entry: 'src/ssr-entry.jsx',
        server: 'src/ssr-server.jsx',
      },
      output: {
        format: 'es',
        entryFileNames: '[name].js',
      },
    },
  },
});
