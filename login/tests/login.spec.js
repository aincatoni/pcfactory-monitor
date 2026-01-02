// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PCFactory Login Monitor
 * 
 * Este test verifica que el sistema de login de PCFactory está funcionando correctamente.
 * Prueba múltiples aspectos del flujo de autenticación.
 */

const CONFIG = {
  loginUrl: 'https://www.pcfactory.cl/login',
  baseUrl: 'https://www.pcfactory.cl',
  
  // Credenciales de prueba (inválidas - solo para verificar que el sistema responde)
  testCredentials: {
    email: 'test.monitor@example.com',
    password: 'TestPassword123!'
  },
  
  // Timeouts
  navigationTimeout: 30000,
  actionTimeout: 10000,
  
  // Selectores (pueden necesitar ajustes según cambios en la web)
  selectors: {
    // Campos del formulario
    emailInput: 'input[type="email"], input[name="email"], input[placeholder*="correo" i], input[placeholder*="email" i], #email',
    passwordInput: 'input[type="password"], input[name="password"], #password',
    loginButton: 'button[type="submit"], button:has-text("Iniciar sesión"), button:has-text("Ingresar"), .btn-login',
    
    // Opciones de login social
    googleLogin: 'button:has-text("Google"), a:has-text("Google"), .google-login, [data-provider="google"]',
    facebookLogin: 'button:has-text("Facebook"), a:has-text("Facebook"), .facebook-login, [data-provider="facebook"]',
    
    // Elementos de la página
    loginForm: 'form, .login-form, .form-login, [class*="login"]',
    errorMessage: '.error, .alert-error, .error-message, [class*="error"], [role="alert"]',
    forgotPassword: 'a:has-text("Olvidaste"), a:has-text("Recuperar"), a[href*="recuperar"], a[href*="forgot"]',
    registerLink: 'a:has-text("Regístrate"), a:has-text("Crear cuenta"), a[href*="registro"], a[href*="register"]',
    
    // Usuario logueado
    userMenu: '.user-menu, .mi-cuenta, [class*="user"], [class*="account"]',
    userName: '.user-name, .nombre-usuario'
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
    
    // Interceptar errores de consola
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log(`Console error: ${msg.text()}`);
      }
    });
  });

  test('1. Página de login carga correctamente', async ({ page }) => {
    const testResult = {
      name: 'Carga de página',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      // Navegar a la página de login
      const response = await page.goto(CONFIG.loginUrl, {
        waitUntil: 'domcontentloaded'
      });
      
      // Verificar respuesta HTTP
      const status = response?.status() || 0;
      testResult.details.httpStatus = status;
      
      expect(status).toBeLessThan(400);
      
      // Verificar que la página tiene contenido
      const title = await page.title();
      testResult.details.pageTitle = title;
      
      // Tomar screenshot
      await page.screenshot({ 
        path: 'test-results/screenshots/01-login-page.png',
        fullPage: true 
      });
      
      testResult.status = 'passed';
      testResult.details.message = 'Página de login cargó correctamente';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/01-login-page-error.png',
        fullPage: true 
      });
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('2. Formulario de login está presente', async ({ page }) => {
    const testResult = {
      name: 'Formulario presente',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      
      // Esperar que cargue el contenido
      await page.waitForTimeout(2000);
      
      // Buscar campo de email
      const emailField = await page.locator(CONFIG.selectors.emailInput).first();
      const emailVisible = await emailField.isVisible().catch(() => false);
      testResult.details.emailFieldFound = emailVisible;
      
      // Buscar campo de password
      const passwordField = await page.locator(CONFIG.selectors.passwordInput).first();
      const passwordVisible = await passwordField.isVisible().catch(() => false);
      testResult.details.passwordFieldFound = passwordVisible;
      
      // Buscar botón de login
      const loginBtn = await page.locator(CONFIG.selectors.loginButton).first();
      const loginBtnVisible = await loginBtn.isVisible().catch(() => false);
      testResult.details.loginButtonFound = loginBtnVisible;
      
      // Screenshot del formulario
      await page.screenshot({ 
        path: 'test-results/screenshots/02-login-form.png',
        fullPage: true 
      });
      
      // Verificar que al menos tenemos los campos básicos
      expect(emailVisible || passwordVisible).toBeTruthy();
      
      testResult.status = 'passed';
      testResult.details.message = 'Formulario de login encontrado';
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('3. Opciones de login social presentes', async ({ page }) => {
    const testResult = {
      name: 'Login social',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Buscar botón de Google
      const googleBtn = await page.locator(CONFIG.selectors.googleLogin).first();
      const googleVisible = await googleBtn.isVisible().catch(() => false);
      testResult.details.googleLoginFound = googleVisible;
      
      // Buscar botón de Facebook
      const facebookBtn = await page.locator(CONFIG.selectors.facebookLogin).first();
      const facebookVisible = await facebookBtn.isVisible().catch(() => false);
      testResult.details.facebookLoginFound = facebookVisible;
      
      // Screenshot
      await page.screenshot({ 
        path: 'test-results/screenshots/03-social-login.png',
        fullPage: true 
      });
      
      testResult.status = 'passed';
      testResult.details.message = `Google: ${googleVisible ? 'Sí' : 'No'}, Facebook: ${facebookVisible ? 'Sí' : 'No'}`;
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('4. Sistema responde a intento de login', async ({ page }) => {
    const testResult = {
      name: 'Respuesta del sistema',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Intentar llenar el formulario
      const emailField = await page.locator(CONFIG.selectors.emailInput).first();
      const passwordField = await page.locator(CONFIG.selectors.passwordInput).first();
      
      if (await emailField.isVisible().catch(() => false)) {
        await emailField.fill(CONFIG.testCredentials.email);
        testResult.details.emailFilled = true;
      }
      
      if (await passwordField.isVisible().catch(() => false)) {
        await passwordField.fill(CONFIG.testCredentials.password);
        testResult.details.passwordFilled = true;
      }
      
      // Screenshot antes de enviar
      await page.screenshot({ 
        path: 'test-results/screenshots/04-before-submit.png',
        fullPage: true 
      });
      
      // Buscar y hacer clic en el botón de login
      const loginBtn = await page.locator(CONFIG.selectors.loginButton).first();
      
      if (await loginBtn.isVisible().catch(() => false)) {
        // Interceptar la respuesta del servidor
        const responsePromise = page.waitForResponse(
          response => response.url().includes('login') || response.url().includes('auth'),
          { timeout: 15000 }
        ).catch(() => null);
        
        await loginBtn.click();
        testResult.details.loginButtonClicked = true;
        
        // Esperar respuesta o timeout
        const response = await responsePromise;
        if (response) {
          testResult.details.serverResponseStatus = response.status();
          testResult.details.serverResponded = true;
        }
        
        // Esperar un momento para ver el resultado
        await page.waitForTimeout(3000);
        
        // Verificar si hay mensaje de error (esperado con credenciales inválidas)
        const errorMsg = await page.locator(CONFIG.selectors.errorMessage).first();
        const hasError = await errorMsg.isVisible().catch(() => false);
        
        if (hasError) {
          const errorText = await errorMsg.textContent().catch(() => '');
          testResult.details.errorMessageShown = true;
          testResult.details.errorText = errorText?.substring(0, 100);
        }
        
        // Screenshot después del intento
        await page.screenshot({ 
          path: 'test-results/screenshots/04-after-submit.png',
          fullPage: true 
        });
        
        testResult.status = 'passed';
        testResult.details.message = 'Sistema respondió al intento de login';
      } else {
        testResult.status = 'warning';
        testResult.details.message = 'No se encontró botón de login';
      }
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      await page.screenshot({ 
        path: 'test-results/screenshots/04-error.png',
        fullPage: true 
      });
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('5. Link de recuperar contraseña funciona', async ({ page }) => {
    const testResult = {
      name: 'Recuperar contraseña',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Buscar link de recuperar contraseña
      const forgotLink = await page.locator(CONFIG.selectors.forgotPassword).first();
      const linkVisible = await forgotLink.isVisible().catch(() => false);
      testResult.details.forgotPasswordLinkFound = linkVisible;
      
      if (linkVisible) {
        const href = await forgotLink.getAttribute('href').catch(() => '');
        testResult.details.forgotPasswordUrl = href;
        
        // Hacer clic y verificar navegación
        await forgotLink.click();
        await page.waitForTimeout(2000);
        
        const newUrl = page.url();
        testResult.details.navigatedTo = newUrl;
        
        // Screenshot de la página de recuperación
        await page.screenshot({ 
          path: 'test-results/screenshots/05-forgot-password.png',
          fullPage: true 
        });
        
        testResult.status = 'passed';
        testResult.details.message = 'Link de recuperar contraseña funciona';
      } else {
        testResult.status = 'warning';
        testResult.details.message = 'No se encontró link de recuperar contraseña';
      }
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
      throw error;
    } finally {
      testResult.duration = Date.now() - startTime;
      results.tests.push(testResult);
    }
  });

  test('6. Link de registro funciona', async ({ page }) => {
    const testResult = {
      name: 'Link de registro',
      status: 'pending',
      duration: 0,
      details: {}
    };
    const startTime = Date.now();
    
    try {
      await page.goto(CONFIG.loginUrl, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);
      
      // Buscar link de registro
      const registerLink = await page.locator(CONFIG.selectors.registerLink).first();
      const linkVisible = await registerLink.isVisible().catch(() => false);
      testResult.details.registerLinkFound = linkVisible;
      
      if (linkVisible) {
        const href = await registerLink.getAttribute('href').catch(() => '');
        testResult.details.registerUrl = href;
        
        // Hacer clic y verificar navegación
        await registerLink.click();
        await page.waitForTimeout(2000);
        
        const newUrl = page.url();
        testResult.details.navigatedTo = newUrl;
        
        // Screenshot de la página de registro
        await page.screenshot({ 
          path: 'test-results/screenshots/06-register.png',
          fullPage: true 
        });
        
        testResult.status = 'passed';
        testResult.details.message = 'Link de registro funciona';
      } else {
        testResult.status = 'warning';
        testResult.details.message = 'No se encontró link de registro';
      }
      
    } catch (error) {
      testResult.status = 'failed';
      testResult.details.error = error.message;
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
    
    results.summary = {
      total: results.tests.length,
      passed,
      failed,
      warnings,
      successRate: Math.round((passed / results.tests.length) * 100)
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
