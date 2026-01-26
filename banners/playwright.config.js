// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './tests',

  // Timeout por test (banner analysis puede tomar tiempo)
  timeout: 360000,

  // Ejecutar tests en paralelo
  fullyParallel: false,
  workers: 1,

  // Retry en caso de fallo
  retries: 0,

  // Reporter
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/banner-report.json' }],
    ['html', { outputFolder: 'playwright-report', open: 'never' }]
  ],

  // Configuración global
  use: {
    // URL base
    baseURL: 'https://www.pcfactory.cl',

    // Timeout para acciones (reducido para evitar bloqueos largos)
    actionTimeout: 10000,

    // Navegación
    navigationTimeout: 30000,

    // Screenshots
    screenshot: 'on',

    // Videos - grabar siempre para debugging
    video: {
      mode: 'on',
      size: { width: 1280, height: 720 }
    },

    // Traces
    trace: 'retain-on-failure',

    // User agent realista
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

    // Viewport
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2,

    // Locale
    locale: 'es-CL',
    timezoneId: 'America/Santiago',
  },

  // Configuración de proyectos (browsers)
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
