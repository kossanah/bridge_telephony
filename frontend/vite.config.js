import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// Path to CRM's local frappe-ui submodule
const frappeUIPath = path.resolve(__dirname, '../../crm/frappe-ui')

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
  const isDev = mode === 'development'
  const frappeui = await importFrappeUIPlugin()

  const config = {
    plugins: [
      frappeui({
        frappeProxy: true,
        lucideIcons: true,
        jinjaBootData: true,
        buildConfig: {
          // Output to CRM's public folder (from bridge_telephony/frontend to crm/www)
          indexHtmlPath: path.resolve(__dirname, 'index.html'),
        },
      }),
      vue(),
      vueJsx(),
      VitePWA({
        registerType: 'autoUpdate',
        devOptions: {
          enabled: true,
        },
        manifest: {
          display: 'standalone',
          name: 'Frappe CRM',
          short_name: 'Frappe CRM',
          start_url: '/crm',
          description:
            'Modern & 100% Open-source CRM tool to supercharge your sales operations',
          icons: [
            {
              src: '/assets/crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-192.maskable.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'maskable',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: '/assets/crm/manifest/manifest-icon-512.maskable.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'maskable',
            },
          ],
        },
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        'frappe-ui': frappeUIPath,
      },
    },
    optimizeDeps: {
      include: [
        'feather-icons',
        'showdown',
        'tailwind.config.js',
        'prosemirror-state',
        'prosemirror-view',
        'lowlight',
        'interactjs',
      ],
    },
  }

  return config
})

async function importFrappeUIPlugin() {
  // Always use CRM's local frappe-ui plugin
  try {
    const module = await import('../../crm/frappe-ui/vite/index.js')
    return module.default
  } catch (error) {
    console.error('Failed to load frappe-ui vite plugin from CRM:', error.message)
    // Fallback to npm package
    const module = await import('frappe-ui/vite')
    return module.default
  }
}
