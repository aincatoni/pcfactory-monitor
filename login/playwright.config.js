// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  
  // Ejecutar tests en serie (uno a la vez)
  fullyParallel: false,
  workers: 1,
  
  // Reintentos en caso de fallo
  retries: 1,
  
  // Timeout por test
  timeout: 60000,
  
  // Reportes
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/login-monitor-report.json' }],
    ['html', { outputFolder: 'playwright-report', open: 'never' }]
  ],
  
  // Configuración global
  use: {
    // URL base
    baseURL: 'https://www.pcfactory.cl',
    
    // Timeout para acciones
    actionTimeout: 15000,
    
    // Navegación
    navigationTimeout: 30000,
    
    // Screenshots
    screenshot: 'on',
    
    // Videos
    video: 'retain-on-failure',
    
    // Traces
    trace: 'retain-on-failure',
    
    // User agent realista
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    
    // Viewport
    viewport: { width: 1280, height: 720 },
    
    // Ignorar HTTPS errors
    ignoreHTTPSErrors: true,
    
    // Headers adicionales
    extraHTTPHeaders: {
      'Accept-Language': 'es-CL,es;q=0.9',
    },
  },

  // Proyectos (navegadores)
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  
  // Directorio de salida
  outputDir: 'test-results/',
});
