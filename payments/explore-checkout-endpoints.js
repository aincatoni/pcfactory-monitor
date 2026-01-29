// Script temporal para explorar endpoints del checkout
const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Array para guardar todas las peticiones
  const requests = [];

  // Interceptar todas las peticiones de red
  page.on('request', request => {
    const url = request.url();
    // Solo guardar peticiones a API de PCFactory
    if (url.includes('pcfactory.cl') || url.includes('api')) {
      requests.push({
        url: url,
        method: request.method(),
        resourceType: request.resourceType(),
        headers: request.headers(),
        postData: request.postData(),
        timestamp: new Date().toISOString()
      });
      console.log(`[REQUEST] ${request.method()} ${url}`);
    }
  });

  // Interceptar respuestas
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('pcfactory.cl') || url.includes('api')) {
      const request = requests.find(r => r.url === url && !r.status);
      if (request) {
        request.status = response.status();
        request.statusText = response.statusText();

        // Intentar capturar el body de la respuesta si es JSON
        try {
          const contentType = response.headers()['content-type'];
          if (contentType && contentType.includes('application/json')) {
            const body = await response.json();
            request.responseBody = body;
          }
        } catch (e) {
          // Ignorar errores al parsear body
        }
      }
      console.log(`[RESPONSE] ${response.status()} ${url}`);
    }
  });

  console.log('\n🔍 EXPLORANDO CHECKOUT DE PCFACTORY\n');

  try {
    // Paso 1: Ir a búsqueda y agregar producto
    console.log('📦 PASO 1: Buscar y agregar producto al carrito');
    await page.goto('https://www.pcfactory.cl/busqueda-avanzada?search=*&size=12&sort=precio,asc');
    await page.waitForSelector('section[data-section-name="Lista productos"]', { timeout: 30000 });
    await page.waitForTimeout(2000);

    // Agregar primer producto disponible
    const addButton = page.locator('section[data-section-name="Lista productos"] button.products__item__info__add-to-cart').first();
    await addButton.click();
    await page.waitForTimeout(3000);

    console.log('✅ Producto agregado al carrito\n');

    // Paso 2: Ir al checkout
    console.log('🛒 PASO 2: Navegar al checkout');
    await page.goto('https://www.pcfactory.cl/checkout');
    await page.waitForTimeout(3000);

    console.log('✅ En página de checkout\n');

    // Paso 3: Continuar como invitado
    console.log('👤 PASO 3: Continuar como invitado');
    const guestButton = page.locator('button:has-text("Continuar como invitado")').first();
    await guestButton.click();
    await page.waitForTimeout(3000);

    console.log('✅ Continuando como invitado\n');

    // Paso 4: Seleccionar tipo de entrega
    console.log('🚚 PASO 4: Seleccionar retiro en tienda');
    const retiroOption = page.locator('label[for="withdraw"], input#withdraw').first();
    await retiroOption.click();
    await page.waitForTimeout(2000);

    // Seleccionar tienda
    const storeInput = page.locator('input.pcf-radio-input[name="store"]').first();
    await storeInput.click({ force: true });
    await page.waitForTimeout(1000);

    const selectStoreButton = page.locator('button:has-text("Seleccionar tienda")').first();
    await selectStoreButton.click();
    await page.waitForTimeout(3000);

    // Continuar
    const continueButton = page.locator('button:has-text("Continuar")').first();
    await continueButton.click({ force: true });
    await page.waitForTimeout(3000);

    console.log('✅ Tipo de entrega seleccionado\n');

    // Paso 5: Completar datos personales
    console.log('📝 PASO 5: Completar formulario de pago');
    await page.locator('input#receipt-name').fill('Test Monitor');
    await page.waitForTimeout(300);
    await page.locator('input#receipt-rut').fill('11.111.111-1');
    await page.waitForTimeout(300);
    await page.locator('input#receipt-phone-number').fill('12345678');
    await page.waitForTimeout(300);
    await page.locator('input#receipt-email').fill('test@test.cl');
    await page.waitForTimeout(300);
    await page.locator('input#receipt-email-confirmation').fill('test@test.cl');
    await page.waitForTimeout(1000);

    console.log('✅ Formulario completado\n');

    // Paso 6: Seleccionar medio de pago (no hacer clic en Pagar)
    console.log('💳 PASO 6: Seleccionar medio de pago');
    const paymentOption = page.locator('input#pmWP[name="payment"], label[for="pmWP"]').first();
    await paymentOption.click({ force: true });
    await page.waitForTimeout(2000);

    console.log('✅ Medio de pago seleccionado\n');

    console.log('⏸️  NO haciendo clic en Pagar para evitar crear orden real\n');

    // Esperar un poco más para capturar todas las peticiones
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('❌ Error durante exploración:', error.message);
  }

  // Guardar resultados
  console.log('\n📊 GUARDANDO RESULTADOS\n');

  // Filtrar solo peticiones relevantes (API calls)
  const apiCalls = requests.filter(r =>
    r.url.includes('/api/') ||
    r.url.includes('/checkout') ||
    r.url.includes('/cart') ||
    r.url.includes('/carro') ||
    r.url.includes('/payment') ||
    r.url.includes('/shipping') ||
    r.url.includes('/order')
  );

  const report = {
    timestamp: new Date().toISOString(),
    totalRequests: requests.length,
    apiCalls: apiCalls.length,
    endpoints: apiCalls.map(r => ({
      url: r.url,
      method: r.method,
      status: r.status,
      resourceType: r.resourceType
    })),
    fullDetails: apiCalls
  };

  fs.writeFileSync('/sessions/eloquent-busy-feynman/checkout-endpoints.json', JSON.stringify(report, null, 2));

  console.log(`✅ Encontradas ${requests.length} peticiones totales`);
  console.log(`✅ Identificadas ${apiCalls.length} llamadas de API relevantes`);
  console.log('✅ Resultados guardados en checkout-endpoints.json\n');

  console.log('🔍 ENDPOINTS DE API ENCONTRADOS:\n');
  const uniqueEndpoints = [...new Set(apiCalls.map(r => `${r.method} ${r.url}`))];
  uniqueEndpoints.forEach(endpoint => {
    console.log(`   ${endpoint}`);
  });

  await browser.close();
  console.log('\n✅ Exploración completada');
})();
