import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    conditions: ['module', 'browser', 'import', 'default'],
  },
  optimizeDeps: {
    include: ['mapbox-gl'],
  },
  server: { port: 5173 },
})
