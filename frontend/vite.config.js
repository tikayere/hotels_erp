import path from 'path'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig(async () => {
  const { default: frappeui } = await import('frappe-ui/vite')

  return {
    plugins: [
      vue(),
      frappeui({
        // Served at /pms; also drives the dev-server site banner.
        frontendRoute: '/pms',
        // Set explicitly rather than relying on the plugin's path-inference
        // (it needs a real bench's sites/common_site_config.json a few
        // directories up to guess right, which isn't there in every
        // checkout/CI layout this repo builds from).
        buildConfig: {
          outDir: '../hotel_erp/public/frontend',
          baseUrl: '/assets/hotel_erp/frontend/',
          indexHtmlPath: '../hotel_erp/www/pms.html',
        },
        // Auto-generates TS-flavoured JSDoc types for these DocTypes from
        // their JSON so editors get field autocomplete on API responses
        // shaped like them (see src/types/doctypes.ts, regenerated on change
        // — do not hand-edit it).
        frappeTypes: {
          input: {
            hotel_erp: ['Reservation', 'Room', 'Room Type', 'Rate Plan'],
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
