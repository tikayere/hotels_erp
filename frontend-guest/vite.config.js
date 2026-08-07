import path from 'path'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig(async () => {
  const { default: frappeui } = await import('frappe-ui/vite')

  return {
    plugins: [
      vue(),
      frappeui({
        // Served at /book; also drives the dev-server site banner. Separate
        // Vite project (not a second entry in frontend/) so the public
        // guest bundle never accidentally pulls in staff-only pages/code,
        // and so it can be built/deployed independently of the /pms SPA.
        frontendRoute: '/book',
        // Set explicitly rather than relying on the plugin's path-inference
        // (see erp/frontend/vite.config.js's identical comment — same
        // reasoning, no real bench checkout above this directory in every
        // layout this repo builds from).
        buildConfig: {
          outDir: '../hotel_erp/public/booking',
          baseUrl: '/assets/hotel_erp/booking/',
          indexHtmlPath: '../hotel_erp/www/book.html',
        },
        frappeTypes: {
          input: {
            hotel_erp: ['Reservation', 'Room Type', 'Rate Plan'],
          },
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
  }
})
