import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    host: true
  },
  build: {
    // Duas páginas: o gerador (index.html) e o Laboratório de Temas, que só funciona
    // onde a API tem LABORATORIO_HABILITADO=1 (o gamma).
    rollupOptions: {
      input: {
        main: 'index.html',
        laboratorio: 'laboratorio.html'
      }
    }
  }
})
