// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PCFactory Login Monitor
 * 
 * Este test verifica que el sistema de login de PCFactory está funcionando correctamente.
 * Usa GitHub Secrets para las credenciales (PCFACTORY_RUT y PCFACTORY_PASSWORD).
 * 
 * Flujo:
 * 1. Ir a pcfactory.cl
 * 2. Hacer hover en "Hola, ingresa" para abrir dropdown
 * 3. Click en "Inicia sesión"
 * 4. Llenar RUT y Contraseña
 * 5. Click en botón de login
 * 6. Verificar que el login fue exitoso
 */

const CONFIG = {
  baseUrl: 'https://www.pcfactory.cl',
  
  // Credenciales desde variables de entorno (GitHub Secrets)
  credentials: {
    rut: process.env.PCFACTORY_RUT || '',
    password: process.env.PCFACTORY_PASSWORD || ''
  },
  
  // Timeouts
  navigationTimeout: 30000,
  actionTimeout: 15000,
  
  // Selectores basados en el análisis del DOM
  selectors: {
    // Dropdown de login en header
    loginDropdownButton: 'button#login-dropdown',
    loginDropdownToggle: '.dropdown-toggle[data-toggle="dropdown"]',
    loginDropdownMenu: '.dropdown-menu[aria-labelledby="login-dropdown"]',
    
    // Link "Inicia sesión" en el dropdown
    iniciarSesionLink: 'a.dropdown-item[href*="login"]',
    
    // Página de login (auth.pcfactory.cl)
    rutInput: 'input#username, input[name="username"]',
    passwordInput: 'input#password, input[name="password"]',
    submitButton: 'button[type="submit"], input[type="submit"], #kc-login',
    
    // Verificación de login exitoso
    userLoggedIn: '.user-name, .nombre-usuario, [data-content-name*="Hola"]',
    miCuentaLink: 'a[href*="mi-cuenta"], a[href*="micuenta"]',
    
    // Mensajes de error
    errorMessage: '.alert-error, .error-message, .kc-feedback-text, [class*="error"]',
    
    // Olvidé contraseña
    forgotPasswordLink: 'a:has-text("Olvidaste"), a:has-text("olvidaste")'
  }
};

// Resultados para el reporte
const results = {
  timestamp: new Date().toISOString(),
  tests: []
};

test.describe('PCFactory Login Monitor', () => {
  
  test.beforeEach(async ({ page }) => {
    // Configurar timeouts
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
      
      // Esperar que cargue el header
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
      });
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('2. Dropdown de login se despliega', async ({ page }) => {
    const testResult = {
      name: 'Dropdown de login',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Buscar el botón de login dropdown
      const loginButton = page.locator('button#login-dropdown, .login-btn, [data-toggle="dropdown"]:has-text("Hola")').first();
      
      // Verificar que existe
      await expect(loginButton).toBeVisible({ timeout: 10000 });
      testResult.details.dropdownButtonFound = true;
      
      // Hacer click para abrir el dropdown
      await loginButton.click();
      await page.waitForTimeout(500);
      
      // Verificar que el dropdown se abrió
      const dropdown = page.locator('.dropdown-menu.show, .dropdown.show .dropdown-menu').first();
      const isDropdownVisible = await dropdown.isVisible().catch(() => false);
      testResult.details.dropdownOpened = isDropdownVisible;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/02-dropdown-open.png',
        fullPage: false 
      });
      
      // Buscar link "Inicia sesión"
      const iniciarSesionLink = page.locator('a.dropdown-item:has-text("Inicia sesión"), a:has-text("Inicia sesión")').first();
      const linkVisible = await iniciarSesionLink.isVisible().catch(() => false);
      testResult.details.iniciarSesionLinkFound = linkVisible;
      
      expect(linkVisible).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Dropdown de login funciona correctamente';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/02-dropdown-error.png',
        fullPage: false 
      });
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('3. Navegación a página de login', async ({ page }) => {
    const testResult = {
      name: 'Navegar a login',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Abrir dropdown
      const loginButton = page.locator('button#login-dropdown, .login-btn, [data-toggle="dropdown"]:has-text("Hola")').first();
      await loginButton.click();
      await page.waitForTimeout(500);
      
      // Click en "Inicia sesión"
      const iniciarSesionLink = page.locator('a.dropdown-item:has-text("Inicia sesión"), a:has-text("Inicia sesión")').first();
      
      // Esperar navegación al hacer click
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
        iniciarSesionLink.click()
      ]);
      
      await page.waitForTimeout(2000);
      
      // Verificar que llegamos a la página de login
      const currentUrl = page.url();
      testResult.details.navigatedTo = currentUrl;
      
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
      testResult.details.message = 'Navegación a página de login exitosa';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/03-login-page-error.png',
        fullPage: false 
      });
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
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Navegar a login
      const loginButton = page.locator('button#login-dropdown, .login-btn, [data-toggle="dropdown"]:has-text("Hola")').first();
      await loginButton.click();
      await page.waitForTimeout(500);
      
      const iniciarSesionLink = page.locator('a.dropdown-item:has-text("Inicia sesión"), a:has-text("Inicia sesión")').first();
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
        iniciarSesionLink.click()
      ]);
      
      await page.waitForTimeout(3000);
      
      // Verificar campos del formulario
      const rutInput = page.locator('input#username, input[name="username"]').first();
      const passwordInput = page.locator('input#password, input[name="password"]').first();
      
      const rutVisible = await rutInput.isVisible({ timeout: 10000 }).catch(() => false);
      const passwordVisible = await passwordInput.isVisible({ timeout: 5000 }).catch(() => false);
      
      testResult.details.rutInputFound = rutVisible;
      testResult.details.passwordInputFound = passwordVisible;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/04-login-form.png',
        fullPage: false 
      });
      
      expect(rutVisible && passwordVisible).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Formulario de login está presente y funcional';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/04-login-form-error.png',
        fullPage: false 
      });
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
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Navegar a login
      const loginButton = page.locator('button#login-dropdown, .login-btn, [data-toggle="dropdown"]:has-text("Hola")').first();
      await loginButton.click();
      await page.waitForTimeout(500);
      
      const iniciarSesionLink = page.locator('a.dropdown-item:has-text("Inicia sesión"), a:has-text("Inicia sesión")').first();
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
        iniciarSesionLink.click()
      ]);
      
      await page.waitForTimeout(3000);
      
      // Llenar formulario
      const rutInput = page.locator('input#username, input[name="username"]').first();
      const passwordInput = page.locator('input#password, input[name="password"]').first();
      
      await rutInput.fill(CONFIG.credentials.rut);
      testResult.details.rutFilled = true;
      
      await passwordInput.fill(CONFIG.credentials.password);
      testResult.details.passwordFilled = true;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/05-credentials-filled.png',
        fullPage: false 
      });
      
      // Buscar y hacer click en el botón de submit
      const submitButton = page.locator('button[type="submit"], input[type="submit"], #kc-login, button:has-text("Iniciar sesión"), button:has-text("Ingresar")').first();
      
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => {}),
        submitButton.click()
      ]);
      
      await page.waitForTimeout(5000);
      
      // Verificar resultado del login
      const currentUrl = page.url();
      testResult.details.redirectedTo = currentUrl;
      
      // Verificar si volvimos a PCFactory (login exitoso)
      const loginSuccess = currentUrl.includes('pcfactory.cl') && !currentUrl.includes('auth.');
      
      // También verificar si hay algún elemento que indique usuario logueado
      const userElement = page.locator('[data-content-name*="Hola"], .user-logged, .mi-cuenta').first();
      const isLoggedIn = await userElement.isVisible().catch(() => false);
      
      testResult.details.loginSuccess = loginSuccess || isLoggedIn;
      
      await page.screenshot({ 
        path: 'test-results/screenshots/05-after-login.png',
        fullPage: false 
      });
      
      // Si hay error, verificar el mensaje
      if (!loginSuccess && !isLoggedIn) {
        const errorElement = page.locator('.alert-error, .kc-feedback-text, [class*="error"]').first();
        const errorVisible = await errorElement.isVisible().catch(() => false);
        if (errorVisible) {
          const errorText = await errorElement.textContent().catch(() => '');
          testResult.details.errorMessage = errorText;
        }
      }
      
      expect(loginSuccess || isLoggedIn).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Login exitoso';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/05-login-error.png',
        fullPage: false 
      });
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
      await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Navegar a login
      const loginButton = page.locator('button#login-dropdown, .login-btn, [data-toggle="dropdown"]:has-text("Hola")').first();
      await loginButton.click();
      await page.waitForTimeout(500);
      
      const iniciarSesionLink = page.locator('a.dropdown-item:has-text("Inicia sesión"), a:has-text("Inicia sesión")').first();
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
        iniciarSesionLink.click()
      ]);
      
      await page.waitForTimeout(3000);
      
      // Buscar link de olvidé contraseña
      const forgotLink = page.locator('a:has-text("Olvidaste"), a:has-text("olvidaste"), a[href*="forgot"]').first();
      const linkVisible = await forgotLink.isVisible().catch(() => false);
      testResult.details.forgotLinkFound = linkVisible;
      
      if (linkVisible) {
        const href = await forgotLink.getAttribute('href').catch(() => '');
        testResult.details.forgotLinkHref = href;
        
        await page.screenshot({ 
          path: 'test-results/screenshots/06-forgot-password.png',
          fullPage: false 
        });
        
        testResult.status = 'passed';
        testResult.details.message = 'Link de recuperar contraseña encontrado';
      } else {
        testResult.status = 'warning';
        testResult.details.message = 'Link de recuperar contraseña no encontrado';
      }
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/06-forgot-password-error.png',
        fullPage: false 
      });
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
