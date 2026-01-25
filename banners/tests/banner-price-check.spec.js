// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const Tesseract = require('tesseract.js');

/**
 * PCFactory Banner Price Monitor
 *
 * Este test verifica que los precios mostrados en los banners del slider principal
 * coincidan con los precios reales de los productos.
 */

const CONFIG = {
  baseUrl: 'https://www.pcfactory.cl',
  screenshotsDir: './test-results/screenshots',

  // Selectores del slider (pueden necesitar ajuste)
  // Nota: Solo queremos banners del carousel principal (no todos los carousels de la página)
  sliderSelectors: [
    '#carousel-home-desktop .carousel-item', // Carousel principal desktop (ESPECÍFICO)
    '#carousel-home-mobile .carousel-item',  // Carousel principal mobile (fallback)
    '.carousel-home .carousel-item',         // Carousel home genérico
    'div[id*="carousel-home"] .carousel-item', // Cualquier carousel home
    '.data-banner-default-carousel',         // Clase específica de banners
  ],

  // Patterns de precio chileno
  pricePatterns: [
    /\$\s*[\d.]+/g,  // $123.456
    /[\d.]+\s*pesos/gi,  // 123.456 pesos
  ],

  // Timeout
  navigationTimeout: 30000,
};

// Resultados globales
const results = {
  timestamp: new Date().toISOString(),
  banners: []
};

/**
 * Extrae TODOS los precios de un texto (elimina puntos de miles)
 * @returns {number[]} Array de precios encontrados
 */
function extractAllPrices(text) {
  if (!text) return [];

  // Buscar patrones de precio más flexibles
  const patterns = [
    /\$\s*([\d.]+)/g,           // $123.456 o $ 123.456
    /([\d.]+)\s*pesos/gi,       // 123.456 pesos
    /precio[:\s]+([\d.]+)/gi,   // precio: 123.456
    /(?:^|[^\d])([\d]{3}\.[\d]{3})/g  // 649.990 (formato chileno sin $)
  ];

  const foundPrices = [];
  const seenPrices = new Set(); // Para evitar duplicados

  for (const pattern of patterns) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const priceStr = match[1];
      if (priceStr) {
        // Remover puntos de miles y convertir a número
        const price = parseInt(priceStr.replace(/\./g, ''), 10);
        // Validar que sea un precio razonable (entre $10.000 y $99.999.990)
        if (!isNaN(price) && price >= 10000 && price < 100000000) {
          if (!seenPrices.has(price)) {
            foundPrices.push(price);
            seenPrices.add(price);
          }
        }
      }
    }
  }

  return foundPrices;
}

/**
 * Extrae texto de una imagen usando OCR (Tesseract)
 */
async function extractTextFromImage(imagePath) {
  try {
    console.log(`  🔍 Ejecutando OCR en imagen...`);

    // Configuración más agresiva para detectar números y símbolos de precio
    const { data: { text } } = await Tesseract.recognize(
      imagePath,
      'eng', // Inglés es mejor para números y símbolos $
      {
        logger: () => {}, // Silenciar logs de Tesseract
        // Configuración para mejorar detección de números y símbolos
        tessedit_char_whitelist: '0123456789$.,% ',
        tessedit_pageseg_mode: Tesseract.PSM.SPARSE_TEXT,
      }
    );

    console.log(`  🔍 OCR resultado: "${text.trim()}"`);
    return text;
  } catch (error) {
    console.log(`  ⚠️ Error en OCR: ${error.message}`);
    return '';
  }
}

/**
 * Detecta TODOS los precios en un banner usando análisis de texto + OCR
 * @returns {number[]} Array de precios encontrados
 */
async function analyzeBannerForPrices(page, bannerElement, screenshotPath) {
  try {
    const allPrices = [];
    const seenPrices = new Set();

    // Helper para agregar precios sin duplicados
    const addPrices = (prices, source) => {
      for (const price of prices) {
        if (!seenPrices.has(price)) {
          allPrices.push(price);
          seenPrices.add(price);
          console.log(`  📍 Precio detectado en ${source}: $${price.toLocaleString('es-CL')}`);
        }
      }
    };

    // 1. Obtener texto visible en el banner (HTML text)
    const bannerText = await bannerElement.innerText();
    addPrices(extractAllPrices(bannerText), 'texto HTML');

    // 2. Buscar en atributos alt/title de imágenes
    const images = await bannerElement.locator('img').all();
    for (const img of images) {
      const alt = await img.getAttribute('alt').catch(() => '');
      const title = await img.getAttribute('title').catch(() => '');
      const src = await img.getAttribute('src').catch(() => '');

      addPrices(extractAllPrices(alt || ''), 'alt de imagen');
      addPrices(extractAllPrices(title || ''), 'title de imagen');
      addPrices(extractAllPrices(src || ''), 'src de imagen');
    }

    // 3. Buscar en todo el HTML interno
    const innerHTML = await bannerElement.innerHTML();
    addPrices(extractAllPrices(innerHTML), 'HTML interno');

    // 4. Último recurso: OCR en el screenshot del banner
    if (screenshotPath && fs.existsSync(screenshotPath)) {
      console.log(`  🔍 Intentando OCR en imagen del banner...`);
      const ocrText = await extractTextFromImage(screenshotPath);
      addPrices(extractAllPrices(ocrText), 'OCR');
    }

    if (allPrices.length === 0) {
      console.log(`  ℹ️ No se detectaron precios en el banner (puede ser promocional)`);
    } else {
      console.log(`  ✅ Total de precios únicos detectados en banner: ${allPrices.length} [${allPrices.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}]`);
    }

    return allPrices;

  } catch (error) {
    console.log(`  ⚠️ Error al analizar banner: ${error.message}`);
    return [];
  }
}

/**
 * Extrae TODOS los precios de una página de producto
 * @returns {number[]} Array de precios encontrados
 */
async function extractProductPrices(page) {
  try {
    const url = page.url();
    const bodyText = await page.locator('body').innerText();
    const allPrices = extractAllPrices(bodyText);

    if (allPrices.length > 0) {
      console.log(`  💰 Precios encontrados en página de productos: ${allPrices.length} [${allPrices.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}]`);
    } else {
      console.log(`  ⚠️ No se encontraron precios en la página de productos`);
    }

    return allPrices;
  } catch (error) {
    console.log(`  ⚠️ No se pudo extraer precios del producto: ${error.message}`);
    return [];
  }
}

/**
 * Compara dos arrays de precios y verifica si todos los precios del banner están en la página
 * @param {number[]} bannerPrices - Precios encontrados en el banner
 * @param {number[]} productPrices - Precios encontrados en la página de productos
 * @returns {{match: boolean, missing: number[], found: number[]}}
 */
function comparePrices(bannerPrices, productPrices) {
  const missing = [];
  const found = [];
  const TOLERANCE_PERCENT = 1; // 1% de tolerancia

  for (const bannerPrice of bannerPrices) {
    let priceFound = false;

    for (const productPrice of productPrices) {
      const difference = Math.abs(productPrice - bannerPrice);
      const percentDiff = (difference / bannerPrice) * 100;

      if (percentDiff < TOLERANCE_PERCENT) {
        found.push(bannerPrice);
        priceFound = true;
        break;
      }
    }

    if (!priceFound) {
      missing.push(bannerPrice);
    }
  }

  return {
    match: missing.length === 0 && bannerPrices.length > 0,
    missing,
    found
  };
}

test.describe('Banner Price Monitor', () => {

  test.beforeAll(async () => {
    // Crear directorio para screenshots
    if (!fs.existsSync(CONFIG.screenshotsDir)) {
      fs.mkdirSync(CONFIG.screenshotsDir, { recursive: true });
    }
  });

  test('Verificar precios en banners del slider principal', async ({ page, context }) => {
    console.log('🎯 Iniciando análisis de banners...\n');

    // 1. Navegar a la homepage
    console.log('📍 Navegando a homepage...');
    await page.goto(CONFIG.baseUrl, { waitUntil: 'networkidle', timeout: CONFIG.navigationTimeout });

    // Esperar que cargue el slider
    await page.waitForTimeout(3000);

    // 2. Intentar encontrar el slider
    console.log('🔍 Buscando slider de banners...\n');

    let sliderFound = false;
    let bannerElements = [];

    for (const selector of CONFIG.sliderSelectors) {
      try {
        const elements = await page.locator(selector).all();
        if (elements.length > 0) {
          console.log(`✅ Slider encontrado con selector: ${selector}`);
          console.log(`📊 Banners encontrados: ${elements.length}\n`);
          bannerElements = elements;
          sliderFound = true;
          break;
        }
      } catch (e) {
        // Intentar siguiente selector
        continue;
      }
    }

    if (!sliderFound) {
      console.log('❌ No se encontró el slider. Intentando captura general...');
      // Capturar screenshot de la página completa para debugging
      await page.screenshot({
        path: path.join(CONFIG.screenshotsDir, 'homepage-full.png'),
        fullPage: true
      });

      // Marcar como warning pero no fallar el test
      results.banners.push({
        index: 0,
        status: 'error',
        error: 'No se encontró el slider en la homepage',
        screenshot: 'homepage-full.png'
      });

      return;
    }

    // 3. Analizar cada banner usando navegación del carousel
    const totalBanners = Math.min(bannerElements.length, 15); // Máximo 15 para evitar timeouts muy largos
    const processedBannerIds = new Set(); // Para detectar cuando vuelve al inicio

    for (let i = 0; i < totalBanners; i++) {
      console.log(`\n🎨 Analizando Banner ${i + 1}/${totalBanners}`);

      const bannerResult = {
        index: i + 1,
        screenshot: `banner-${i + 1}.png`,
        bannerPrices: [],
        productPrices: [],
        productUrl: null,
        status: 'pending',
        priceMatch: null,
        matchedPrices: [],
        missingPrices: [],
        error: null
      };

      try {
        // Verificar que la página principal sigue abierta
        if (page.isClosed()) {
          console.log(`  ⚠️ Página cerrada, terminando análisis`);
          break;
        }

        // Esperar a que el carousel se estabilice
        await page.waitForTimeout(1000);

        // Obtener el banner activo actual
        const activeBanner = await page.locator('#carousel-home-desktop .carousel-item.active').first();

        // Obtener índice real del banner usando data-gtag-index
        const gtagIndex = await activeBanner.getAttribute('data-gtag-index').catch(() => null);
        const realBannerIndex = gtagIndex ? parseInt(gtagIndex, 10) : null;

        // Obtener ID único del banner para detectar duplicados
        const bannerClass = await activeBanner.getAttribute('class').catch(() => '');
        const bannerId = bannerClass.match(/default-carousel-([a-f0-9-]+)/)?.[1] || `banner-${i}`;

        if (processedBannerIds.has(bannerId)) {
          console.log(`  ⏭️ Banner ya procesado (carousel volvió al inicio), terminando análisis`);
          break;
        }
        processedBannerIds.add(bannerId);

        // Actualizar el índice del banner con el índice real
        if (realBannerIndex !== null) {
          bannerResult.index = realBannerIndex;
          bannerResult.screenshot = `banner-${realBannerIndex}.png`;
          console.log(`  📍 Banner real: #${realBannerIndex}`);
        }

        // Capturar screenshot del carousel completo (no del elemento individual)
        const carouselContainer = await page.locator('#carousel-home-desktop .carousel-inner').first();
        const screenshotFilename = realBannerIndex !== null ? `banner-${realBannerIndex}.png` : `banner-${i + 1}.png`;
        const screenshotPath = path.join(CONFIG.screenshotsDir, screenshotFilename);

        try {
          await carouselContainer.screenshot({ path: screenshotPath, timeout: 5000 });
          console.log(`  📸 Screenshot guardado: ${screenshotFilename}`);
        } catch (screenshotError) {
          console.log(`  ⚠️ No se pudo capturar screenshot: ${screenshotError.message}`);
        }

        // Analizar TODOS los precios en el banner (incluye OCR si screenshot existe)
        const bannerPrices = await analyzeBannerForPrices(page, activeBanner, screenshotPath);
        bannerResult.bannerPrices = bannerPrices;

        if (bannerPrices.length === 0) {
          console.log(`  ℹ️ Banner sin precios detectados (posiblemente promocional)`);
          bannerResult.status = 'no_price';
          results.banners.push(bannerResult);

          // Avanzar al siguiente banner
          const nextButton = await page.locator('#carousel-home-desktop .carousel-control-next').first();
          await nextButton.click().catch(() => console.log('  ⚠️ No se pudo hacer click en siguiente'));
          continue;
        }

        // Obtener el link del banner
        const link = await activeBanner.locator('a').first();
        const href = await link.getAttribute('href');

        if (!href) {
          console.log(`  ⚠️ Banner sin link`);
          bannerResult.status = 'no_link';
          bannerResult.error = 'Banner sin link de destino';
          results.banners.push(bannerResult);
          continue;
        }

        // Construir URL completa
        let targetUrl = href;
        if (href.startsWith('/')) {
          targetUrl = CONFIG.baseUrl + href;
        }

        bannerResult.productUrl = targetUrl;
        console.log(`  🔗 Link destino: ${targetUrl}`);

        // Abrir link en nueva pestaña para no perder el estado del slider
        const newPage = await context.newPage();

        try {
          console.log(`  🌐 Navegando al producto...`);
          await newPage.goto(targetUrl, { waitUntil: 'networkidle', timeout: CONFIG.navigationTimeout });
          await newPage.waitForTimeout(2000);

          // Screenshot de la página de destino
          await newPage.screenshot({
            path: path.join(CONFIG.screenshotsDir, `banner-${i + 1}-product.png`)
          });

          // Extraer TODOS los precios de la página de productos
          const productPrices = await extractProductPrices(newPage);
          bannerResult.productPrices = productPrices;

          if (productPrices.length === 0) {
            console.log(`  ⚠️ No se pudo extraer precios de la página de productos`);
            bannerResult.status = 'no_product_price';
            bannerResult.error = 'No se encontraron precios en la página de destino';
          } else {
            // Comparar arrays de precios
            const comparison = comparePrices(bannerPrices, productPrices);

            if (comparison.match) {
              console.log(`  ✅ ¡Todos los precios del banner coinciden con la página!`);
              console.log(`     Precios coincidentes: ${comparison.found.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}`);
              bannerResult.status = 'match';
              bannerResult.priceMatch = true;
              bannerResult.matchedPrices = comparison.found;
            } else {
              console.log(`  ❌ Algunos precios del banner NO coinciden con la página`);
              console.log(`     Banner: ${bannerPrices.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}`);
              console.log(`     Producto: ${productPrices.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}`);
              if (comparison.found.length > 0) {
                console.log(`     ✅ Coincidentes: ${comparison.found.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}`);
              }
              if (comparison.missing.length > 0) {
                console.log(`     ❌ Faltantes: ${comparison.missing.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}`);
              }
              bannerResult.status = 'mismatch';
              bannerResult.priceMatch = false;
              bannerResult.matchedPrices = comparison.found;
              bannerResult.missingPrices = comparison.missing;
            }
          }

        } catch (error) {
          console.log(`  ❌ Error al navegar al producto: ${error.message}`);
          bannerResult.status = 'error';
          bannerResult.error = error.message;
        } finally {
          await newPage.close();
        }

      } catch (error) {
        console.log(`  ❌ Error al procesar banner: ${error.message}`);
        bannerResult.status = 'error';
        bannerResult.error = error.message;

        // Si el error es porque la página se cerró, terminar
        if (error.message.includes('Target page, context or browser has been closed')) {
          results.banners.push(bannerResult);
          console.log(`  🛑 Navegador cerrado, terminando análisis`);
          break;
        }
      }

      results.banners.push(bannerResult);

      // Avanzar al siguiente banner (excepto en el último)
      if (i < totalBanners - 1) {
        try {
          // Verificar que la página sigue abierta antes de hacer click
          if (page.isClosed()) {
            console.log(`  🛑 Página cerrada, terminando análisis`);
            break;
          }

          const nextButton = await page.locator('#carousel-home-desktop .carousel-control-next').first();
          await nextButton.click();
          console.log(`  ➡️ Avanzando al siguiente banner...`);
          await page.waitForTimeout(1500); // Esperar animación del carousel
        } catch (clickError) {
          console.log(`  ⚠️ No se pudo avanzar al siguiente banner: ${clickError.message}`);
          // Si no puede avanzar, es mejor terminar
          break;
        }
      }
    }

    // 4. Guardar resultados
    const resultsPath = './test-results/banner-price-results.json';
    fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
    console.log(`\n✅ Resultados guardados en: ${resultsPath}`);

    // Resumen
    const total = results.banners.length;
    const withPrice = results.banners.filter(b => b.bannerPrice).length;
    const matched = results.banners.filter(b => b.priceMatch === true).length;
    const mismatched = results.banners.filter(b => b.priceMatch === false).length;

    console.log(`\n📊 RESUMEN:`);
    console.log(`   Total banners: ${total}`);
    console.log(`   Con precio: ${withPrice}`);
    console.log(`   ✅ Coinciden: ${matched}`);
    console.log(`   ❌ No coinciden: ${mismatched}`);
  });
});
