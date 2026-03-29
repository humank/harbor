import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Strands A2AServer uses JSON-RPC at root path
      '/a2a': {
        target: 'http://localhost:8200',
        rewrite: (path) => path.replace(/^\/a2a/, ''),
      },
      '/.well-known': 'http://localhost:8200',
      '/agents': 'http://localhost:8200',
    },
  },
})
