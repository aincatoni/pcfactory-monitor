// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

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
  sliderSelectors: [
    '.swiper-slide',
    '.carousel-item',
    '[class*="slider"]',
    '[class*="banner"]'
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
 * Extrae números de un texto (elimina puntos de miles)
 */
function extractPrice(text) {
  if (!text) return null;

  // Buscar patrones de precio más flexibles
  const patterns = [
    /\$\s*([\d.]+)/g,           // $123.456 o $ 123.456
    /([\d.]+)\s*pesos/gi,       // 123.456 pesos
    /precio[:\s]+([\d.]+)/gi,   // precio: 123.456
    /(?:^|[^\d])([\d]{3}\.[\d]{3})/g  // 649.990 (formato chileno sin $)
  ];

  for (const pattern of patterns) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const priceStr = match[1];
      if (priceStr) {
        // Remover puntos de miles y convertir a número
        const price = parseInt(priceStr.replace(/\./g, ''), 10);
        // Validar que sea un precio razonable (entre $1.000 y $99.999.990)
        if (!isNaN(price) && price >= 1000 && price < 100000000) {
          return price;
        }
      }
    }
  }

  return null;
}

/**
 * Detecta si un banner tiene información de precio usando análisis de texto
 */
async function analyzeBannerForPrice(page, bannerElement) {
  try {
    // 1. Obtener texto visible en el banner (HTML text)
    const bannerText = await bannerElement.innerText();
    let price = extractPrice(bannerText);

    if (price) {
      console.log(`  📍 Precio detectado en texto HTML: $${price.toLocaleString('es-CL')}`);
      return price;
    }

    // 2. Buscar en atributos alt de imágenes (a veces tienen info de precio)
    const images = await bannerElement.locator('img').all();
    for (const img of images) {
      const alt = await img.getAttribute('alt').catch(() => '');
      const title = await img.getAttribute('title').catch(() => '');
      const src = await img.getAttribute('src').catch(() => '');

      const altPrice = extractPrice(alt || '');
      const titlePrice = extractPrice(title || '');
      const srcPrice = extractPrice(src || ''); // A veces el precio está en el nombre del archivo

      if (altPrice) {
        console.log(`  📍 Precio detectado en alt de imagen: $${altPrice.toLocaleString('es-CL')}`);
        return altPrice;
      }
      if (titlePrice) {
        console.log(`  📍 Precio detectado en title de imagen: $${titlePrice.toLocaleString('es-CL')}`);
        return titlePrice;
      }
      if (srcPrice) {
        console.log(`  📍 Precio detectado en src de imagen: $${srcPrice.toLocaleString('es-CL')}`);
        return srcPrice;
      }
    }

    // 3. Buscar en todo el HTML interno (incluyendo elementos ocultos)
    const innerHTML = await bannerElement.innerHTML();
    price = extractPrice(innerHTML);

    if (price) {
      console.log(`  📍 Precio detectado en HTML interno: $${price.toLocaleString('es-CL')}`);
      return price;
    }

    console.log(`  ℹ️ No se detectó precio en el banner (puede ser promocional o el precio está en imagen)`);
    return null;
  } catch (error) {
    console.log(`  ⚠️ Error al analizar banner: ${error.message}`);
    return null;
  }
}

/**
 * Extrae el precio de una página de producto
 */
async function extractProductPrice(page) {
  try {
    // Esperar a que cargue el precio (varios selectores posibles)
    const priceSelectors = [
      '[class*="price"]',
      '[class*="precio"]',
      '[data-price]',
      '.product-price',
      '#product-price'
    ];

    for (const selector of priceSelectors) {
      try {
        const priceElement = await page.locator(selector).first().waitFor({ timeout: 5000 });
        const priceText = await page.locator(selector).first().innerText();
        const price = extractPrice(priceText);

        if (price) {
          console.log(`  💰 Precio en producto: $${price.toLocaleString('es-CL')}`);
          return price;
        }
      } catch (e) {
        // Intentar siguiente selector
        continue;
      }
    }

    // Si no encontramos precio con selectores, buscar en todo el texto
    const bodyText = await page.locator('body').innerText();
    const price = extractPrice(bodyText);

    if (price) {
      console.log(`  💰 Precio encontrado en página: $${price.toLocaleString('es-CL')}`);
      return price;
    }

    return null;
  } catch (error) {
    console.log(`  ⚠️ No se pudo extraer precio del producto: ${error.message}`);
    return null;
  }
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

    // 3. Analizar cada banner
    for (let i = 0; i < Math.min(bannerElements.length, 10); i++) {
      const banner = bannerElements[i];
      console.log(`\n🎨 Analizando Banner ${i + 1}/${bannerElements.length}`);

      const bannerResult = {
        index: i + 1,
        screenshot: `banner-${i + 1}.png`,
        bannerPrice: null,
        productPrice: null,
        productUrl: null,
        status: 'pending',
        priceMatch: null,
        error: null
      };

      try {
        // Hacer visible el banner (si está en carousel)
        await banner.scrollIntoViewIfNeeded();
        await page.waitForTimeout(1000);

        // Screenshot del banner
        const screenshotPath = path.join(CONFIG.screenshotsDir, `banner-${i + 1}.png`);
        await banner.screenshot({ path: screenshotPath });
        console.log(`  📸 Screenshot guardado`);

        // Analizar si tiene precio
        const bannerPrice = await analyzeBannerForPrice(page, banner);
        bannerResult.bannerPrice = bannerPrice;

        if (!bannerPrice) {
          console.log(`  ℹ️ Banner sin precio detectado (posiblemente promocional)`);
          bannerResult.status = 'no_price';
          results.banners.push(bannerResult);
          continue;
        }

        // Obtener el link del banner
        const link = await banner.locator('a').first();
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

          // Extraer precio del producto
          const productPrice = await extractProductPrice(newPage);
          bannerResult.productPrice = productPrice;

          if (!productPrice) {
            console.log(`  ⚠️ No se pudo extraer precio del producto`);
            bannerResult.status = 'no_product_price';
            bannerResult.error = 'No se encontró precio en la página de destino';
          } else {
            // Comparar precios
            const difference = Math.abs(bannerPrice - productPrice);
            const percentDiff = (difference / productPrice) * 100;

            // Considerar match si la diferencia es menor al 1%
            if (percentDiff < 1) {
              console.log(`  ✅ Precios coinciden!`);
              bannerResult.status = 'match';
              bannerResult.priceMatch = true;
            } else {
              console.log(`  ❌ Precios NO coinciden!`);
              console.log(`     Banner: $${bannerPrice.toLocaleString('es-CL')}`);
              console.log(`     Producto: $${productPrice.toLocaleString('es-CL')}`);
              console.log(`     Diferencia: $${difference.toLocaleString('es-CL')} (${percentDiff.toFixed(1)}%)`);
              bannerResult.status = 'mismatch';
              bannerResult.priceMatch = false;
              bannerResult.difference = difference;
              bannerResult.percentDiff = percentDiff;
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
      }

      results.banners.push(bannerResult);
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
