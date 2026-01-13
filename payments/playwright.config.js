// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * PCFactory Payment Monitor - Playwright Configuration
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './tests',
  
  /* Run tests in files in parallel */
  fullyParallel: false, // Secuencial para evitar conflictos con el carrito
  
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 1,
  
  /* Opt out of parallel tests - important for cart-based tests */
  workers: 1,
  
  /* Reporter to use */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list']
  ],
  
  /* Shared settings for all the projects below */
  use: {
    /* Base URL */
    baseURL: 'https://www.pcfactory.cl',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Video - grabar siempre para el dashboard */
    video: 'on',
    
    /* Timeouts - aumentados para evitar race conditions */
    actionTimeout: 20000,
    navigationTimeout: 45000,
    
    /* Viewport */
    viewport: { width: 1280, height: 720 },
    
    /* Locale for Chile */
    locale: 'es-CL',
    timezoneId: 'America/Santiago',
    
    /* SlowMo - pequeña pausa entre acciones para estabilidad */
    launchOptions: {
      slowMo: 100, // 100ms entre cada acción
    },
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Usar modo headless en CI
        headless: !!process.env.CI,
      },
    },
  ],

  /* Output folder for test artifacts */
  outputDir: 'test-results/',
  
  /* Global timeout for each test */
  timeout: 180000, // 3 minutos por test (flujo completo de checkout)
  
  /* Expect timeout */
  expect: {
    timeout: 15000
  },
});
