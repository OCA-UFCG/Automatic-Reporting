import { defineConfig } from 'vite'

// O FastAPI monta a tela em /painel (ver main.py); sem `base`, os assets
// seriam pedidos na raiz e voltariam 404 em produção.
export default defineConfig({
  base: '/painel/',
  server: {
    port: 5174,
    host: true
  }
})
