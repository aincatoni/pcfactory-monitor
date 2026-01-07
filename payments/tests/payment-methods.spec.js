// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PCFactory Payment Methods Monitor
 * 
 * Este test verifica que todos los medios de pago estén funcionando
 * correctamente, llevando el flujo hasta la pasarela de pago.
 * 
 * Estrategia: Buscar productos baratos con alto stock para evitar
 * problemas de disponibilidad.
 */

// Configuración
const CONFIG = {
  // URL de búsqueda ordenada por precio menor a mayor
  searchUrl: 'https://www.pcfactory.cl/busqueda-avanzada?search=*&size=12&sort=precio,asc',
  
  // Datos de prueba para checkout (invitado)
  testData: {
    nombre: 'Test',
    apellido: 'Monitor',
    rut: '11.111.111-1',
    telefono: '12345678',  // 8 dígitos sin el +569
    email: 'test.monitor@pcfactory.cl'
  },
  
  // Medios de pago a probar
  paymentMethods: [
    {
      id: 'ETPAY',
      name: 'Transferencia ETPay',
      selector: 'input#pmETP[name="payment"], label[for="pmETP"], li#pmETP',
      expectedUrl: ['etpay', 'khipu', 'etpayment'],
      expectedTitle: ['etpay', 'khipu', 'transferencia']
    },
    {
      id: 'BANCOESTADO',
      name: 'Compraquí',
      selector: 'input#pmBCA[name="payment"], label[for="pmBCA"], li#pmBCA',
      expectedUrl: ['bancoestado', 'compraqui', 'compraaqui'],
      expectedTitle: ['bancoestado', 'compra']
    },
    {
      id: 'CLICKTOPAY',
      name: 'Mastercard Click to Pay',
      selector: 'input#pmCTP[name="payment"], label[for="pmCTP"], li#pmCTP',
      expectedUrl: ['clicktopay', 'mastercard', 'src.mastercard', 'compraqui'],
      expectedTitle: ['click to pay', 'mastercard']
    },
    {
      id: 'WEBPAY_DEBITO',
      name: 'Tarjeta de Débito (Webpay)',
      selector: 'input#pmWPD[name="payment"], label[for="pmWPD"], li#pmWPD',
      expectedUrl: ['webpay', 'transbank'],
      expectedTitle: ['webpay', 'transbank']
    },
    {
      id: 'WEBPAY_CREDITO',
      name: 'Tarjeta de Crédito (Webpay)',
      selector: 'input#pmWP[name="payment"], label[for="pmWP"], li#pmWP',
      expectedUrl: ['webpay', 'transbank'],
      expectedTitle: ['webpay', 'transbank']
    }
  ],
  
  // Timeouts - valores más generosos para evitar race conditions
  navigationTimeout: 45000,
  actionTimeout: 20000,
  gatewayTimeout: 60000
};

// Resultados globales para el reporte
const testResults = {
  timestamp: new Date().toISOString(),
  results: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0
  }
};

test.describe('PCFactory Payment Methods Monitor', () => {
  
  test.beforeEach(async ({ page }) => {
    // Configurar timeouts
    page.setDefaultTimeout(CONFIG.actionTimeout);
    page.setDefaultNavigationTimeout(CONFIG.navigationTimeout);
  });

  // Test para cada medio de pago
  for (const paymentMethod of CONFIG.paymentMethods) {
    test(`Verificar ${paymentMethod.name}`, async ({ page, context }) => {
      const result = {
        paymentMethod: paymentMethod.name,
        paymentId: paymentMethod.id,
        status: 'UNKNOWN',
        steps: [],
        error: null,
        gatewayReached: false,
        gatewayUrl: null,
        duration: 0
      };
      
      const startTime = Date.now();
      
      try {
        // Paso 1: Ir a búsqueda y encontrar producto con alto stock
        result.steps.push({ step: 'Buscar producto con stock', status: 'running' });
        
        // Ir a la búsqueda ordenada por precio menor a mayor
        await page.goto(CONFIG.searchUrl, { waitUntil: 'domcontentloaded' });
        await expect(page).toHaveURL(/pcfactory\.cl/);
        
        // Esperar a que cargue la sección de productos de la PLP (NO el carrusel)
        // El contenedor principal es: section[data-section-name="Lista productos"]
        await page.waitForSelector('section[data-section-name="Lista productos"]', { timeout: 30000 });
        
        // Esperar a que aparezcan los botones de agregar al carro dentro de la PLP
        await page.waitForSelector('section[data-section-name="Lista productos"] button.products__item__info__add-to-cart', { timeout: 30000 });
        
        // Esperar un poco más para que Vue termine de renderizar
        await page.waitForTimeout(2000);
        
        // Buscar productos con alto stock (+100 Unid.) dentro de la PLP
        const plpSection = page.locator('section[data-section-name="Lista productos"]');
        const highStockProducts = plpSection.locator('a.products__item:has(span.products__item__info__unidades:has-text("+100"))');
        const highStockCount = await highStockProducts.count();
        
        let selectedProduct;
        
        if (highStockCount > 0) {
          // Seleccionar un producto aleatorio con alto stock
          const randomIndex = Math.floor(Math.random() * Math.min(highStockCount, 5));
          selectedProduct = highStockProducts.nth(randomIndex);
          console.log(`    Encontrados ${highStockCount} productos con +100 unidades, seleccionando índice ${randomIndex}`);
        } else {
          // Si no hay productos con +100, tomar cualquier producto de la PLP
          const allProducts = plpSection.locator('a.products__item');
          const productCount = await allProducts.count();
          if (productCount > 0) {
            const randomIndex = Math.floor(Math.random() * Math.min(productCount, 5));
            selectedProduct = allProducts.nth(randomIndex);
            console.log(`    No hay productos con +100 unidades, seleccionando producto ${randomIndex} de ${productCount}`);
          }
        }
        
        if (!selectedProduct) {
          throw new Error('No se encontraron productos en la PLP');
        }
        
        // Obtener el botón de agregar al carrito dentro del producto seleccionado
        const addToCartButton = selectedProduct.locator('button.products__item__info__add-to-cart');
        
        if (await addToCartButton.count() === 0) {
          throw new Error('No se encontró el botón de agregar al carrito');
        }
        
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 2: Agregar al carrito
        result.steps.push({ step: 'Agregar al carrito', status: 'running' });
        
        await addToCartButton.scrollIntoViewIfNeeded();
        await addToCartButton.waitFor({ state: 'visible', timeout: 10000 });
        await addToCartButton.click();
        
        // Esperar confirmación (modal o cambio en carrito)
        await page.waitForTimeout(3000);
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 3: Ir al carrito/checkout
        result.steps.push({ step: 'Ir al checkout', status: 'running' });
        
        // Intentar ir directamente al checkout
        await page.goto('https://www.pcfactory.cl/checkout', { waitUntil: 'domcontentloaded' });
        
        // Verificar que estamos en el flujo de checkout
        await page.waitForURL(/checkout|carro/, { timeout: 10000 });
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 4: Continuar como invitado (Inicio de sesión)
        result.steps.push({ step: 'Continuar como invitado', status: 'running' });
        
        // Esperar a que aparezca la página de inicio de sesión
        await page.waitForTimeout(2000);
        
        // Selector del botón "Continuar como invitado" - está en el div derecho (right)
        // Usamos el texto para diferenciarlo del botón "Inicia sesión"
        const guestButton = page.locator('button.pcf-btn--five:has-text("Continuar como invitado")').first();
        
        await guestButton.waitFor({ state: 'visible', timeout: 10000 });
        await guestButton.click();
        
        // Esperar navegación al siguiente paso (Tipo de Entrega)
        await page.waitForTimeout(3000);
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 5: Seleccionar tipo de entrega (Retiro en tienda)
        result.steps.push({ step: 'Seleccionar retiro en tienda', status: 'running' });
        
        // Esperar a que cargue la página de tipo de entrega
        await page.waitForSelector('text=Selecciona el método de entrega', { timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(2000);
        
        // Hacer clic en "Retiro en tienda" - usar el label o el div contenedor
        const retiroOption = page.locator('label[for="withdraw"], input#withdraw, div.method-option:has-text("Retiro en tienda")').first();
        await retiroOption.waitFor({ state: 'visible', timeout: 10000 });
        await retiroOption.click();
        
        // Esperar a que aparezca el modal de selección de tienda
        await page.waitForSelector('text=Disponibilidad en tienda', { timeout: 10000 });
        await page.waitForTimeout(2000);
        
        // Seleccionar la primera tienda disponible
        const storeInput = page.locator('input.pcf-radio-input[name="store"]').first();
        await storeInput.waitFor({ state: 'attached', timeout: 10000 });
        await storeInput.click({ force: true });
        await page.waitForTimeout(1000);
        
        // Hacer clic en "Seleccionar tienda" para cerrar el modal
        const selectStoreButton = page.locator('button:has-text("Seleccionar tienda")').first();
        await selectStoreButton.waitFor({ state: 'visible', timeout: 10000 });
        await selectStoreButton.click();
        
        // IMPORTANTE: Esperar a que el modal se cierre completamente
        await page.waitForTimeout(3000);
        
        // Verificar que el modal se cerró esperando que desaparezca
        await page.waitForSelector('text=Disponibilidad en tienda', { state: 'hidden', timeout: 10000 }).catch(() => {});
        
        // Ahora buscar el botón Continuar que está FUERA del modal
        // Usar un selector más específico para el botón principal de continuar
        const continueButton = page.locator('button.pcf-btn--five:has-text("Continuar"), a.pcf-btn:has-text("Continuar")').first();
        await continueButton.waitFor({ state: 'visible', timeout: 15000 });
        
        // Scroll hacia el botón para asegurarse de que está visible
        await continueButton.scrollIntoViewIfNeeded();
        await page.waitForTimeout(500);
        
        // Click con force para evitar problemas de interceptación
        await continueButton.click({ force: true });
        
        // Esperar navegación al paso de Pago
        await page.waitForURL(/checkout.*pago|checkout\/pago/, { timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(3000);
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 6: Completar datos personales (página de Pago)
        result.steps.push({ step: 'Completar datos personales', status: 'running' });
        
        // Esperar a que cargue la página de pago con el formulario
        await page.waitForSelector('input#receipt-name', { timeout: 15000 });
        await page.waitForTimeout(1000);
        
        // Llenar formulario con los selectores correctos
        await page.locator('input#receipt-name').fill(CONFIG.testData.nombre + ' ' + CONFIG.testData.apellido);
        await page.waitForTimeout(300);
        
        await page.locator('input#receipt-rut').fill(CONFIG.testData.rut);
        await page.waitForTimeout(300);
        
        await page.locator('input#receipt-phone-number').fill(CONFIG.testData.telefono);
        await page.waitForTimeout(300);
        
        await page.locator('input#receipt-email').fill(CONFIG.testData.email);
        await page.waitForTimeout(300);
        
        await page.locator('input#receipt-email-confirmation').fill(CONFIG.testData.email);
        await page.waitForTimeout(500);
        
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 7: Seleccionar medio de pago
        result.steps.push({ step: `Seleccionar ${paymentMethod.name}`, status: 'running' });
        
        // Esperar a que aparezcan los medios de pago
        await page.waitForSelector('text=Selecciona tu medio de pago', { timeout: 15000 }).catch(() => {});
        await page.waitForTimeout(1000);
        
        // Seleccionar el medio de pago específico usando force click (radio buttons ocultos)
        const paymentOption = page.locator(paymentMethod.selector).first();
        await paymentOption.waitFor({ state: 'attached', timeout: 10000 });
        await paymentOption.click({ force: true });
        await page.waitForTimeout(1500);
        result.steps[result.steps.length - 1].status = 'passed';
        
        // Paso 8: Hacer clic en Pagar y verificar redirección a pasarela
        result.steps.push({ step: 'Clic en Pagar y verificar pasarela', status: 'running' });
        
        // Esperar un momento para que el medio de pago se registre
        await page.waitForTimeout(1000);
        
        // Buscar el botón Pagar con múltiples selectores
        const pagarButton = page.locator('button.pcf-btn--five:has-text("Pagar"), button:has-text("Pagar"), button.pcf-btn:has-text("Pagar")').first();
        await pagarButton.scrollIntoViewIfNeeded();
        await pagarButton.waitFor({ state: 'visible', timeout: 10000 });
        
        console.log(`    Haciendo clic en botón Pagar...`);
        
        // Hacer clic y esperar navegación a la pasarela
        await Promise.all([
          page.waitForURL((url) => {
            const urlStr = url.toString().toLowerCase();
            return paymentMethod.expectedUrl.some(expected => urlStr.includes(expected)) ||
                   !urlStr.includes('pcfactory.cl');
          }, { timeout: CONFIG.gatewayTimeout }),
          pagarButton.click()
        ]);
        
        // Verificar que llegamos a la pasarela
        const currentUrl = page.url().toLowerCase();
        const gatewayReached = paymentMethod.expectedUrl.some(expected => currentUrl.includes(expected)) ||
                              !currentUrl.includes('pcfactory.cl');
        
        if (gatewayReached) {
          result.gatewayReached = true;
          result.gatewayUrl = page.url();
          result.steps[result.steps.length - 1].status = 'passed';
          result.status = 'PASSED';
        } else {
          throw new Error(`No se redirigió a la pasarela esperada. URL actual: ${page.url()}`);
        }
        
      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.steps[result.steps.length - 1].status = 'failed';
        
        // Tomar screenshot del error
        await page.screenshot({ 
          path: `./test-results/error-${paymentMethod.id}-${Date.now()}.png`,
          fullPage: true 
        }).catch(() => {});
        
      } finally {
        result.duration = Date.now() - startTime;
        testResults.results.push(result);
        testResults.summary.total++;
        
        if (result.status === 'PASSED') {
          testResults.summary.passed++;
        } else {
          testResults.summary.failed++;
        }
        
        // Limpiar carrito para el siguiente test
        try {
          await page.goto('https://www.pcfactory.cl/carro', { waitUntil: 'domcontentloaded' });
          const removeButtons = page.locator('[data-action="remove"], .btn-remove, button:has-text("Eliminar")');
          const count = await removeButtons.count();
          for (let i = 0; i < count; i++) {
            await removeButtons.first().click().catch(() => {});
            await page.waitForTimeout(500);
          }
        } catch (e) {
          // Ignorar errores de limpieza
        }
      }
      
      // Assertion final
      expect(result.status).toBe('PASSED');
    });
  }
});

// Hook para generar reporte al finalizar
test.afterAll(async () => {
  const fs = require('fs');
  const reportPath = './test-results/payment-monitor-report.json';
  
  try {
    fs.mkdirSync('./test-results', { recursive: true });
    fs.writeFileSync(reportPath, JSON.stringify(testResults, null, 2));
    console.log('\n========================================');
    console.log('RESUMEN DE MONITOREO DE MEDIOS DE PAGO');
    console.log('========================================');
    console.log(`Timestamp: ${testResults.timestamp}`);
    console.log(`Total: ${testResults.summary.total}`);
    console.log(`✅ Passed: ${testResults.summary.passed}`);
    console.log(`❌ Failed: ${testResults.summary.failed}`);
    console.log('----------------------------------------');
    
    for (const result of testResults.results) {
      const icon = result.status === 'PASSED' ? '✅' : '❌';
      console.log(`${icon} ${result.paymentMethod}: ${result.status}`);
      if (result.gatewayUrl) {
        console.log(`   Gateway: ${result.gatewayUrl}`);
      }
      if (result.error) {
        console.log(`   Error: ${result.error}`);
      }
    }
    console.log('========================================\n');
  } catch (e) {
    console.error('Error generating report:', e);
  }
});
