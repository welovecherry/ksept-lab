import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward any /api/* request to the Flask backend on port 5001.
      // (5000 is taken by macOS AirPlay Receiver, so we use 5001.)
      // The browser only ever talks to 5173, so there is no cross-origin call.
      '/api': 'http://localhost:5001',
    },
  },
})
