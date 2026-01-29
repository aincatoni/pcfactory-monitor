// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Configuración de Playwright para el monitor de endpoints del checkout
 *
 * Este monitor hace llamadas directas a la API, no requiere navegador
 */
module.exports = defineConfig({
  testDir: './tests',

  // Timeout para cada test (30 segundos)
  timeout: 30 * 1000,

  // Timeout global para toda la suite (5 minutos)
  globalTimeout: 5 * 60 * 1000,

  // Reintentos en caso de fallo
  retries: 2,

  // Número de workers (paralelismo)
  workers: 1, // Usar 1 worker para evitar rate limiting

  // Reporter
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['html', { outputFolder: 'playwright-report', open: 'never' }]
  ],

  use: {
    // Base URL para las APIs
    baseURL: 'https://api.pcfactory.cl',

    // Headers comunes
    extraHTTPHeaders: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'User-Agent': 'PCFactory-Monitor/1.0'
    },

    // Timeout para requests de API
    actionTimeout: 10 * 1000,

    // Tracing en caso de fallo
    trace: 'retain-on-failure',

    // Screenshot en caso de fallo (no aplica para API tests, pero lo dejamos)
    screenshot: 'only-on-failure',
  },

  // Proyectos - solo necesitamos uno para API tests
  projects: [
    {
      name: 'API Tests',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
});
