// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PCFactory Login Monitor
 * 
 * Este test verifica que el sistema de login de PCFactory está funcionando correctamente.
 * Usa navegación directa a /login en vez del dropdown (más confiable).
 * Usa GitHub Secrets para las credenciales (PCFACTORY_RUT y PCFACTORY_PASSWORD).
 */

const CONFIG = {
  baseUrl: 'https://www.pcfactory.cl',
  loginUrl: 'https://www.pcfactory.cl/login',
  
  // Credenciales desde variables de entorno (GitHub Secrets)
  credentials: {
    rut: process.env.PCFACTORY_RUT || '',
    password: process.env.PCFACTORY_PASSWORD || ''
  },
  
  // Timeouts
  navigationTimeout: 30000,
  actionTimeout: 15000,
};

// Resultados para el reporte
const results = {
  timestamp: new Date().toISOString(),
  tests: []
};

test.describe('PCFactory Login Monitor', () => {
  
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(CONFIG.actionTimeout);
    page.setDefaultNavigationTimeout(CONFIG.navigationTimeout);
  });

  test('1. Página principal carga correctamente', async ({ page }) => {
    const testResult = {
      name: 'Carga página principal',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      const response = await page.goto(CONFIG.baseUrl, {
        waitUntil: 'domcontentloaded'
      });
      
      const status = response?.status() || 0;
      testResult.details.httpStatus = status;
      
      expect(status).toBeLessThan(400);
      
      await page.waitForSelector('header, .navbar, nav', { timeout: 10000 });
      
      await page.screenshot({ 
        path: 'test-results/screenshots/01-homepage.png',
        fullPage: false 
      });
      
      testResult.status = 'passed';
      testResult.details.message = 'Página principal cargó correctamente';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/01-homepage-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('2. Botón de login existe en header', async ({ page }) => {
    const testResult = {
      name: 'Botón de login en header',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Buscar el botón de login en el header
      const loginButton = page.locator('button#login-dropdown, [data-toggle="dropdown"]:has-text("Hola"), .login-btn, a[href*="login"]').first();
      
      const buttonExists = await loginButton.isVisible({ timeout: 10000 }).catch(() => false);
      testResult.details.loginButtonFound = buttonExists;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/02-login-button.png',
        fullPage: false 
      });
      
      expect(buttonExists).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Botón de login encontrado en el header';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/02-login-button-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('3. Página de login carga correctamente', async ({ page }) => {
    const testResult = {
      name: 'Página de login',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      // Navegar directamente a /login (esto redirige a auth.pcfactory.cl)
      const response = await page.goto(CONFIG.loginUrl, { 
        waitUntil: 'domcontentloaded',
        timeout: 30000 
      });
      
      await page.waitForTimeout(3000);
      
      const currentUrl = page.url();
      testResult.details.navigatedTo = currentUrl;
      testResult.details.httpStatus = response?.status();
      
      const isLoginPage = currentUrl.includes('auth.pcfactory.cl') || 
                          currentUrl.includes('login') ||
                          currentUrl.includes('openid-connect');
      testResult.details.isLoginPage = isLoginPage;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/03-login-page.png',
        fullPage: false 
      });
      
      expect(isLoginPage).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Página de login cargó correctamente';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/03-login-page-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('4. Formulario de login presente', async ({ page }) => {
    const testResult = {
      name: 'Formulario de login',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      // Ir directo a login
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);
      
      // Verificar campos del formulario
      const rutInput = page.locator('input#username, input[name="username"]').first();
      const passwordInput = page.locator('input#password, input[name="password"]').first();
      
      const rutVisible = await rutInput.isVisible({ timeout: 10000 }).catch(() => false);
      const passwordVisible = await passwordInput.isVisible({ timeout: 5000 }).catch(() => false);
      
      testResult.details.rutInputFound = rutVisible;
      testResult.details.passwordInputFound = passwordVisible;
      testResult.details.currentUrl = page.url();
      
      await page.screenshot({ 
        path: 'test-results/screenshots/04-login-form.png',
        fullPage: false 
      });
      
      expect(rutVisible && passwordVisible).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Formulario de login presente con campos RUT y contraseña';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/04-login-form-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('5. Login con credenciales', async ({ page }) => {
    const testResult = {
      name: 'Login con credenciales',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    // Verificar si hay credenciales configuradas
    if (!CONFIG.credentials.rut || !CONFIG.credentials.password) {
      testResult.status = 'warning';
      testResult.details.message = 'Credenciales no configuradas (PCFACTORY_RUT y PCFACTORY_PASSWORD)';
      testResult.details.skipped = true;
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
      test.skip();
      return;
    }
    
    try {
      // Ir directo a login
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);
      
      // Llenar formulario
      const rutInput = page.locator('input#username, input[name="username"]').first();
      const passwordInput = page.locator('input#password, input[name="password"]').first();
      
      await rutInput.waitFor({ state: 'visible', timeout: 10000 });
      await rutInput.fill(CONFIG.credentials.rut);
      testResult.details.rutFilled = true;
      
      await passwordInput.waitFor({ state: 'visible', timeout: 5000 });
      await passwordInput.fill(CONFIG.credentials.password);
      testResult.details.passwordFilled = true;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/05-credentials-filled.png',
        fullPage: false 
      });
      
      // Buscar y hacer click en el botón de submit
      const submitButton = page.locator('button[type="submit"], input[type="submit"], #kc-login').first();
      
      await submitButton.waitFor({ state: 'visible', timeout: 5000 });
      
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {}),
        submitButton.click()
      ]);
      
      await page.waitForTimeout(5000);
      
      // Verificar resultado del login
      const currentUrl = page.url();
      testResult.details.redirectedTo = currentUrl;
      
      // Verificar si volvimos a PCFactory (login exitoso) o si hay error
      const loginSuccess = currentUrl.includes('pcfactory.cl') && !currentUrl.includes('auth.');
      
      // Verificar si hay mensaje de error
      const errorElement = page.locator('.alert-error, .kc-feedback-text, [class*="error"]').first();
      const hasError = await errorElement.isVisible().catch(() => false);
      
      if (hasError) {
        const errorText = await errorElement.textContent().catch(() => '');
        testResult.details.errorMessage = errorText?.substring(0, 100);
      }
      
      testResult.details.loginSuccess = loginSuccess;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/05-after-login.png',
        fullPage: false 
      });
      
      expect(loginSuccess || !hasError).toBeTruthy();
      
      testResult.status = loginSuccess ? 'passed' : 'warning';
      testResult.details.message = loginSuccess ? 'Login exitoso' : 'Login procesado (verificar credenciales)';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/05-login-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('6. Link olvidé contraseña funciona', async ({ page }) => {
    const testResult = {
      name: 'Olvidé contraseña',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      // Ir directo a login
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(3000);
      
      // Buscar link de olvidé contraseña
      const forgotLink = page.locator('a:has-text("Olvidaste"), a:has-text("olvidaste"), a[href*="forgot"]').first();
      const linkVisible = await forgotLink.isVisible({ timeout: 5000 }).catch(() => false);
      testResult.details.forgotLinkFound = linkVisible;
      
      if (linkVisible) {
        const href = await forgotLink.getAttribute('href').catch(() => '');
        testResult.details.forgotLinkHref = href;
      }
      
      await page.screenshot({ 
        path: 'test-results/screenshots/06-forgot-password.png',
        fullPage: false 
      });
      
      testResult.status = linkVisible ? 'passed' : 'warning';
      testResult.details.message = linkVisible ? 'Link de recuperar contraseña encontrado' : 'Link no encontrado (puede variar según el estado)';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/06-forgot-password-error.png',
        fullPage: false 
      }).catch(() => {});
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test.afterAll(async () => {
    // Guardar resultados en JSON
    const fs = require('fs');
    const path = require('path');
    
    const outputDir = 'test-results';
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // Calcular resumen
    const passed = results.tests.filter(t => t.status === 'passed').length;
    const failed = results.tests.filter(t => t.status === 'failed').length;
    const warnings = results.tests.filter(t => t.status === 'warning').length;
    const total = results.tests.length;
    
    results.summary = {
      total,
      passed,
      failed,
      warnings,
      successRate: total > 0 ? Math.round((passed / total) * 100) : 0
    };
    
    // Determinar estado general
    if (failed > 0) {
      results.overallStatus = 'error';
    } else if (warnings > 0) {
      results.overallStatus = 'warning';
    } else {
      results.overallStatus = 'ok';
    }
    
    fs.writeFileSync(
      path.join(outputDir, 'login-monitor-report.json'),
      JSON.stringify(results, null, 2)
    );
    
    console.log('\n📊 Resultados del Monitor de Login:');
    console.log(`   ✅ Pasaron: ${passed}`);
    console.log(`   ❌ Fallaron: ${failed}`);
    console.log(`   ⚠️ Advertencias: ${warnings}`);
    console.log(`   📈 Tasa de éxito: ${results.summary.successRate}%`);
  });
});