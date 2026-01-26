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
  nextButtonSelectors: [
    '#carousel-home-desktop .carousel-control-next',
    '#carousel-home-mobile .carousel-control-next',
    '.carousel-control-next',
    '.swiper-button-next',
    '.slick-next',
    'button[aria-label="Next"]',
    'button[aria-label="Siguiente"]',
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
    /\$\s*([\d.]+)/g,                    // $123.456 o $ 123.456
    /([\d.]+)\s*pesos/gi,                // 123.456 pesos
    /precio[:\s]+([\d.]+)/gi,            // precio: 123.456
    /(?:^|[^\d])([\d]{3}\.[\d]{3,})/g,   // 649.990 o 1.299.990 (formato chileno con punto)
    /(?:^|[\s\-\(\[])([\d]{5,7})(?:[\s\-\)\]]|$)/g // 24990, 649990, 1299990 (solo si están rodeados de espacios/símbolos)
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
 * Extrae precios desde OCR con reglas más estrictas para evitar falsos positivos
 * @returns {number[]} Array de precios encontrados
 */
function extractPricesFromOCR(text) {
  if (!text) return [];

  const dollarGroupedPattern = /\$\s*([\d]{1,3}(?:[.,][\d]{3})+)/g;
  const dollarPlainPattern = /\$\s*([\d]{5,7})/g;
  const pesosPattern = /([\d]{1,3}(?:[.,][\d]{3})+)\s*pesos/gi;
  const dotPattern = /([\d]{1,3}(?:[.,][\d]{3})+)/g;
  const plainPattern = /(?:^|[^\d])(\d{5,7})(?:[^\d]|$)/g;

  const foundPrices = [];
  const seenPrices = new Set();

  const textLower = text.toLowerCase();
  const globalCurrencyHint = text.includes('$')
    || textLower.includes('pesos')
    || textLower.includes('precio')
    || textLower.includes('oferta')
    || textLower.includes('promo')
    || textLower.includes('descto')
    || textLower.includes('descuento');

  const lines = text.split('\n');
  for (const line of lines) {
    const lower = line.toLowerCase();
    const dotMatches = [...line.matchAll(dotPattern)];
    const hasDotPriceEnding = dotMatches.some((match) => match[1].endsWith('990'));
    const hasCurrencyHint = line.includes('$')
      || lower.includes('pesos')
      || lower.includes('precio')
      || lower.includes('oferta')
      || lower.includes('promo')
      || lower.includes('descto')
      || lower.includes('descuento')
      || dotMatches.length >= 2
      || hasDotPriceEnding
      || globalCurrencyHint;
    if (!hasCurrencyHint) {
      continue;
    }

    const candidates = [];
    const isBoundary = (ch) => !ch || /[^0-9A-Za-z]/.test(ch);
    const addCandidate = (match, requireEnding990 = false) => {
      const fullMatch = match[0];
      const startIndex = match.index ?? 0;
      const before = line[startIndex - 1];
      const after = line[startIndex + fullMatch.length];
      if (!isBoundary(before) || !isBoundary(after)) {
        return;
      }
      const priceStr = match[1] || fullMatch;
      if (requireEnding990 && !priceStr.endsWith('990')) {
        return;
      }
      candidates.push(priceStr);
    };

    for (const match of line.matchAll(dollarGroupedPattern)) {
      addCandidate(match);
    }
    for (const match of line.matchAll(dollarPlainPattern)) {
      addCandidate(match, true);
    }
    for (const match of line.matchAll(pesosPattern)) {
      addCandidate(match);
    }
    if (dotMatches.length >= 2 || hasDotPriceEnding || globalCurrencyHint || lower.includes('oferta') || lower.includes('promo')) {
      for (const match of dotMatches) {
        addCandidate(match);
      }
    }

    if (hasCurrencyHint) {
      for (const match of line.matchAll(plainPattern)) {
        const priceStr = match[1];
        if (priceStr && priceStr.endsWith('990')) {
          candidates.push(priceStr);
        }
      }
    }

    const parsedCandidates = candidates
      .map((priceStr) => {
        const normalized = priceStr.replace(/,/g, '.');
        const price = parseInt(normalized.replace(/\./g, ''), 10);
        return { priceStr, price };
      })
      .filter(({ price }) => !isNaN(price) && price >= 10000 && price < 5000000);

    const hasLowPriceInLine = parsedCandidates.some(({ price }) => price < 100000);

    for (const { priceStr, price } of parsedCandidates) {
      if (!seenPrices.has(price)) {
        foundPrices.push(price);
        seenPrices.add(price);
      }

      if (hasLowPriceInLine && price >= 500000 && price <= 699999 && price % 1000 === 990) {
        const trimmedPrice = price - 500000;
        if (trimmedPrice >= 10000 && trimmedPrice < 100000) {
          if (!seenPrices.has(trimmedPrice)) {
            foundPrices.push(trimmedPrice);
            seenPrices.add(trimmedPrice);
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
async function extractTextFromImage(imagePath, options = {}) {
  try {
    console.log(`  🔍 Ejecutando OCR en imagen...`);
    const whitelist = options.whitelist || '0123456789$.,% ';
    const psm = options.psm || Tesseract.PSM.SPARSE_TEXT;

    // Configuración más agresiva para detectar números y símbolos de precio
    const { data: { text } } = await Tesseract.recognize(
      imagePath,
      'eng', // Inglés es mejor para números y símbolos $
      {
        logger: () => {}, // Silenciar logs de Tesseract
        // Configuración para mejorar detección de números y símbolos
        tessedit_char_whitelist: whitelist,
        tessedit_pageseg_mode: psm,
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
async function analyzeBannerForPrices(page, bannerElement, ocrScreenshotPaths) {
  try {
    const allPrices = [];
    const seenPrices = new Set();
    const priceCounts = new Map();

    // Helper para agregar precios sin duplicados
    const addPrices = (prices, source) => {
      for (const price of prices) {
        priceCounts.set(price, (priceCounts.get(price) || 0) + 1);
        if (!seenPrices.has(price)) {
          allPrices.push(price);
          seenPrices.add(price);
          console.log(`  📍 Precio detectado en ${source}: $${price.toLocaleString('es-CL')}`);
        }
      }
    };

    // OCR es la fuente más confiable para precios en banners
    const maxOcrPrices = 4;
    for (const screenshotPath of ocrScreenshotPaths) {
      if (!screenshotPath || !fs.existsSync(screenshotPath)) {
        continue;
      }
      if (allPrices.length >= maxOcrPrices) {
        break;
      }
      console.log(`  🔍 Intentando OCR en imagen del banner...`);
      const primaryOcrText = await extractTextFromImage(screenshotPath, { psm: Tesseract.PSM.SPARSE_TEXT });
      const primaryPrices = extractPricesFromOCR(primaryOcrText);
      addPrices(primaryPrices, 'OCR');
      if (primaryPrices.length === 0) {
        const fallbackOcrText = await extractTextFromImage(screenshotPath, { psm: Tesseract.PSM.SINGLE_BLOCK });
        addPrices(extractPricesFromOCR(fallbackOcrText), 'OCR (fallback)');
      }
      if (screenshotPath.includes('img-bottom') && allPrices.length < 3) {
        const lineOcrText = await extractTextFromImage(screenshotPath, {
          psm: Tesseract.PSM.SINGLE_LINE,
          whitelist: '0123456789$.'
        });
        addPrices(extractPricesFromOCR(lineOcrText), 'OCR (line)');
      }
    }

    if (allPrices.length === 0) {
      console.log(`  ℹ️ No se detectaron precios en el banner (puede ser promocional)`);
    } else {
      console.log(`  ✅ Total de precios únicos detectados en banner: ${allPrices.length} [${allPrices.map(p => '$' + p.toLocaleString('es-CL')).join(', ')}]`);
    }

    const countsObject = Object.fromEntries(
      Array.from(priceCounts.entries()).map(([price, count]) => [String(price), count])
    );
    return { prices: allPrices, counts: countsObject };

  } catch (error) {
    console.log(`  ⚠️ Error al analizar banner: ${error.message}`);
    return { prices: [], counts: {} };
  }
}

/**
 * Extrae TODOS los precios de una página de producto
 * @returns {number[]} Array de precios encontrados
 */
async function extractProductPrices(page) {
  try {
    const priceLocators = [
      '[data-testid*="price"]',
      '[data-qa*="price"]',
      '[class*="precio"]',
      '[class*="price"]',
    ];
    let combinedText = '';

    for (const selector of priceLocators) {
      const count = await page.locator(selector).count();
      if (count > 0) {
        const texts = await page.locator(selector).allInnerTexts();
        combinedText += `\n${texts.join('\n')}`;
      }
    }

    if (!combinedText.trim()) {
      combinedText = await page.locator('body').innerText();
    }

    const allPrices = extractAllPrices(combinedText);

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

function isPriceInList(price, prices, tolerancePercent) {
  for (const listPrice of prices) {
    const difference = Math.abs(listPrice - price);
    const percentDiff = (difference / price) * 100;
    if (percentDiff < tolerancePercent) {
      return true;
    }
  }
  const priceTail = price % 1000;
  for (const listPrice of prices) {
    if (listPrice % 1000 !== priceTail) {
      continue;
    }
    if (Math.abs(listPrice - price) <= 30000) {
      return true;
    }
  }
  return false;
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
    if (isPriceInList(bannerPrice, productPrices, TOLERANCE_PERCENT)) {
      found.push(bannerPrice);
    } else {
      missing.push(bannerPrice);
    }
  }

  return {
    match: missing.length === 0 && bannerPrices.length > 0,
    missing,
    found
  };
}

function filterBannerPricesForComparison(bannerPrices, priceCounts, productPrices) {
  const filtered = [];
  const ignored = [];
  const TOLERANCE_PERCENT = 1;

  for (const price of bannerPrices) {
    const count = priceCounts[String(price)] || 1;
    const matchesProduct = isPriceInList(price, productPrices, TOLERANCE_PERCENT);
    if (matchesProduct || count >= 2) {
      filtered.push(price);
    } else {
      ignored.push(price);
    }
  }

  return { filtered, ignored };
}

async function deriveSliderRootSelector(page, itemSelector) {
  try {
    const rootSelector = await page.locator(itemSelector).first().evaluate((el) => {
      const root = el.closest('.carousel') || el.closest('[id*="carousel"]') || el.closest('[class*="carousel"]');
      if (!root) return null;
      if (root.id) return `#${root.id}`;
      root.setAttribute('data-banner-root', 'true');
      return '[data-banner-root="true"]';
    });
    return rootSelector;
  } catch (error) {
    return null;
  }
}

async function pauseSlider(page, sliderRootSelector) {
  try {
    if (!sliderRootSelector) return;
    await page.addStyleTag({
      content: `
        .carousel-item { transition: none !important; }
        .swiper-wrapper, .slick-track { transition: none !important; }
      `
    });
    await page.evaluate((selector) => {
      const root = document.querySelector(selector);
      if (!root) return;
      root.setAttribute('data-interval', 'false');
      root.setAttribute('data-bs-interval', 'false');
      root.setAttribute('data-pause', 'hover');
      root.setAttribute('data-bs-pause', 'hover');
      if (window.bootstrap && window.bootstrap.Carousel) {
        try {
          const instance = window.bootstrap.Carousel.getInstance(root) || new window.bootstrap.Carousel(root);
          instance.pause();
        } catch (e) {
          // ignore
        }
      }
      if (window.$ && window.$.fn && typeof window.$.fn.carousel === 'function') {
        try {
          window.$(root).carousel('pause');
        } catch (e) {
          // ignore
        }
      }
    }, sliderRootSelector);
  } catch (error) {
    console.log(`  ⚠️ No se pudo pausar el slider: ${error.message}`);
  }
}

async function getCarouselItemsMeta(page, sliderRootSelector, sliderItemSelector) {
  try {
    const meta = await page.evaluate(({ rootSelector, itemSelector }) => {
      const root = rootSelector ? document.querySelector(rootSelector) : null;
      const container = root || document;
      const items = Array.from(container.querySelectorAll(itemSelector));
      return items.map((el, index) => ({
        domIndex: index,
        gtagIndex: (() => {
          const direct = el.getAttribute('data-gtag-index');
          if (direct) return direct;
          const inner = el.querySelector('[data-gtag-index]');
          return inner ? inner.getAttribute('data-gtag-index') : null;
        })()
      }));
    }, { rootSelector: sliderRootSelector, itemSelector: sliderItemSelector });

    return meta;
  } catch (error) {
    return [];
  }
}

async function goToCarouselIndex(page, sliderRootSelector, index) {
  if (!sliderRootSelector) return false;
  try {
    return await page.evaluate(({ selector, targetIndex }) => {
      const root = document.querySelector(selector);
      if (!root) return false;

      if (window.bootstrap && window.bootstrap.Carousel) {
        try {
          const instance = window.bootstrap.Carousel.getInstance(root) || new window.bootstrap.Carousel(root);
          instance.to(targetIndex);
          return true;
        } catch (e) {
          // ignore
        }
      }

      if (window.$ && window.$.fn && typeof window.$.fn.carousel === 'function') {
        try {
          window.$(root).carousel(targetIndex);
          return true;
        } catch (e) {
          // ignore
        }
      }

      const indicator = root.querySelector(`[data-slide-to="${targetIndex}"], [data-bs-slide-to="${targetIndex}"]`);
      if (indicator) {
        indicator.click();
        return true;
      }

      return false;
    }, { selector: sliderRootSelector, targetIndex: index });
  } catch (error) {
    return false;
  }
}

async function getActiveBanner(page, sliderRootSelector, sliderItemSelector) {
  const candidateSelectors = [];
  if (sliderRootSelector) {
    candidateSelectors.push(
      `${sliderRootSelector} .carousel-item.active`,
      `${sliderRootSelector} .swiper-slide-active`,
      `${sliderRootSelector} .slick-slide.slick-active`
    );
  }
  if (sliderItemSelector) {
    candidateSelectors.push(
      `${sliderItemSelector}.active`,
      `${sliderItemSelector}.swiper-slide-active`,
      `${sliderItemSelector}.slick-active`
    );
  }

  for (const selector of candidateSelectors) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      return locator;
    }
  }

  return page.locator(sliderItemSelector).first();
}

async function getBannerGtagIndex(bannerElement) {
  try {
    let gtagIndex = await bannerElement.getAttribute('data-gtag-index');
    if (!gtagIndex) {
      const innerElement = await bannerElement.locator('[data-gtag-index]').first();
      const count = await bannerElement.locator('[data-gtag-index]').count();
      if (count > 0) {
        gtagIndex = await innerElement.getAttribute('data-gtag-index');
      }
    }
    return gtagIndex;
  } catch (error) {
    return null;
  }
}

async function getCarouselGtagIndexes(page, sliderRootSelector) {
  try {
    return await page.evaluate((selector) => {
      const root = selector ? document.querySelector(selector) : document;
      if (!root) return [];
      const values = new Set();
      const nodes = root.querySelectorAll('[data-gtag-index]');
      for (const node of nodes) {
        const value = node.getAttribute('data-gtag-index');
        if (value) values.add(value);
      }
      return Array.from(values);
    }, sliderRootSelector);
  } catch (error) {
    return [];
  }
}

async function getCarouselIndicatorIndexes(page, sliderRootSelector) {
  if (!sliderRootSelector) return [];
  try {
    return await page.evaluate((selector) => {
      const root = document.querySelector(selector);
      if (!root) return [];
      const indicators = root.querySelectorAll('[data-slide-to], [data-bs-slide-to]');
      const values = new Set();
      for (const indicator of indicators) {
        const raw = indicator.getAttribute('data-bs-slide-to') || indicator.getAttribute('data-slide-to');
        if (raw === null) continue;
        const value = parseInt(raw, 10);
        if (!isNaN(value)) {
          values.add(value);
        }
      }
      return Array.from(values).sort((a, b) => a - b);
    }, sliderRootSelector);
  } catch (error) {
    return [];
  }
}

async function clickNextBanner(page, sliderRootSelector) {
  const selectors = [];
  if (sliderRootSelector) {
    selectors.push(
      `${sliderRootSelector} .carousel-control-next`,
      `${sliderRootSelector} .swiper-button-next`,
      `${sliderRootSelector} .slick-next`
    );
  }
  selectors.push(...CONFIG.nextButtonSelectors);

  for (const selector of selectors) {
    const button = page.locator(selector).first();
    if (await button.count()) {
      await button.click();
      return true;
    }
  }
  return false;
}

async function getPrimaryBannerHref(bannerElement) {
  try {
    return await bannerElement.evaluate((el) => {
      const images = Array.from(el.querySelectorAll('img'));
      let bestImage = null;
      let bestImageArea = 0;
      for (const img of images) {
        const rect = img.getBoundingClientRect();
        const area = rect.width * rect.height;
        if (area > bestImageArea) {
          bestImageArea = area;
          bestImage = img;
        }
      }
      if (bestImage) {
        const imageAnchor = bestImage.closest('a[href]');
        if (imageAnchor) {
          return imageAnchor.getAttribute('href');
        }
      }

      const anchors = Array.from(el.querySelectorAll('a[href]'));
      let bestHref = null;
      let bestArea = 0;

      for (const anchor of anchors) {
        const rect = anchor.getBoundingClientRect();
        const style = window.getComputedStyle(anchor);
        const visible = rect.width > 0
          && rect.height > 0
          && style.display !== 'none'
          && style.visibility !== 'hidden'
          && style.opacity !== '0';
        if (!visible) continue;
        const area = rect.width * rect.height;
        if (area > bestArea) {
          bestArea = area;
          bestHref = anchor.getAttribute('href');
        }
      }

      return bestHref;
    });
  } catch (error) {
    return null;
  }
}

async function captureImageFromUrl(context, imageUrl, outputPath) {
  const imagePage = await context.newPage();
  const outputPaths = [];
  try {
    await imagePage.setContent(`<img src="${imageUrl}" />`, { waitUntil: 'domcontentloaded' });
    const img = imagePage.locator('img');
    await img.waitFor({ state: 'visible', timeout: 10000 });
    await img.screenshot({ path: outputPath, scale: 'device' });
    outputPaths.push(outputPath);

    const bbox = await img.boundingBox().catch(() => null);
    if (bbox) {
      const cropHeight = Math.max(1, bbox.height * 0.45);
      const cropConfigs = [
        { label: 'top', y: Math.max(0, bbox.y) },
        { label: 'center', y: Math.max(0, bbox.y + (bbox.height - cropHeight) / 2) },
        { label: 'bottom', y: Math.max(0, bbox.y + bbox.height - cropHeight) },
      ];
      for (const config of cropConfigs) {
        const cropPath = outputPath.replace(/\.png$/, `-${config.label}.png`);
        const clip = {
          x: Math.max(0, bbox.x),
          y: config.y,
          width: Math.max(1, bbox.width),
          height: cropHeight,
        };
        await imagePage.screenshot({ path: cropPath, clip, scale: 'device' });
        outputPaths.push(cropPath);
      }
    }
  } catch (error) {
    console.log(`  ⚠️ No se pudo capturar imagen desde URL: ${error.message}`);
  } finally {
    await imagePage.close();
  }
  return outputPaths;
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
    await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded', timeout: CONFIG.navigationTimeout });

    // Esperar que cargue el slider
    await page.waitForTimeout(3000);

    // 2. Intentar encontrar el slider
    console.log('🔍 Buscando slider de banners...\n');

    let sliderFound = false;
    let sliderItemSelector = null;
    let sliderRootSelector = null;

    for (const selector of CONFIG.sliderSelectors) {
      try {
        const count = await page.locator(selector).count();
        if (count > 0) {
          console.log(`✅ Slider encontrado con selector: ${selector}`);
          console.log(`📊 Banners encontrados: ${count}\n`);
          sliderItemSelector = selector;
          sliderRootSelector = await deriveSliderRootSelector(page, selector);
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

    if (sliderRootSelector) {
      console.log(`🛑 Pausando slider principal...`);
      await pauseSlider(page, sliderRootSelector);
    }

    // 3. Analizar cada banner usando navegación del carousel
    const bannerMeta = await getCarouselItemsMeta(page, sliderRootSelector, sliderItemSelector);
    const bannersWithIndex = bannerMeta
      .filter((item) => item.gtagIndex && !isNaN(parseInt(item.gtagIndex, 10)))
      .map((item) => ({ ...item, gtagIndex: parseInt(item.gtagIndex, 10) }))
      .sort((a, b) => a.gtagIndex - b.gtagIndex);
    const uniqueBanners = [];
    const seenGtagIndexes = new Set();
    for (const banner of bannersWithIndex) {
      if (seenGtagIndexes.has(banner.gtagIndex)) continue;
      seenGtagIndexes.add(banner.gtagIndex);
      uniqueBanners.push(banner);
    }

    const orderedBanners = uniqueBanners.length > 0 ? uniqueBanners : bannerMeta;
    const indicatorIndexes = await getCarouselIndicatorIndexes(page, sliderRootSelector);
    const useIndicators = indicatorIndexes.length > 0;
    const totalBanners = Math.min(useIndicators ? indicatorIndexes.length : orderedBanners.length, 15); // Máximo 15 para evitar timeouts muy largos
    const processedBannerIds = new Set(); // Para detectar cuando vuelve al inicio
    const processedGtagIndexes = new Set();

    let lastBannerSignature = null;
    for (let i = 0; i < totalBanners; i++) {
      const loopIndex = i + 1;
      console.log(`\n🎨 Analizando posición ${loopIndex}/${totalBanners} del carousel`);

      const bannerResult = {
        index: loopIndex,
        screenshot: `banner-${loopIndex}.png`,
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

        const targetIndicatorIndex = useIndicators ? indicatorIndexes[i] : null;
        if (useIndicators && sliderRootSelector) {
          const moved = await goToCarouselIndex(page, sliderRootSelector, targetIndicatorIndex);
          if (moved) {
            await page.waitForTimeout(1500);
          }
        }

        // Esperar a que el carousel se estabilice después de la animación
        await page.waitForTimeout(2000);

        // Obtener el banner activo actual
        let activeBanner = await getActiveBanner(page, sliderRootSelector, sliderItemSelector);
        const bannerDataElement = useIndicators && targetIndicatorIndex !== null
          ? page.locator(sliderItemSelector).nth(targetIndicatorIndex)
          : activeBanner;
        const bannerElement = bannerDataElement;
        let bannerClass = await bannerElement.getAttribute('class').catch(() => '');
        let bannerSignature = bannerClass;
        if (useIndicators && lastBannerSignature && bannerSignature === lastBannerSignature) {
          const moved = await clickNextBanner(page, sliderRootSelector);
          if (moved) {
            await page.waitForTimeout(1500);
            activeBanner = await getActiveBanner(page, sliderRootSelector, sliderItemSelector);
            bannerClass = await bannerElement.getAttribute('class').catch(() => '');
            bannerSignature = bannerClass;
          }
        }
        lastBannerSignature = bannerSignature;

        // Obtener índice real del banner usando data-gtag-index
        // Preferir el banner activo para evitar desalineación con el screenshot
        let gtagIndex = await getBannerGtagIndex(bannerElement);

        const realBannerIndex = gtagIndex ? parseInt(gtagIndex, 10) : null;

        // Mostrar identificación del banner
        if (realBannerIndex !== null) {
          console.log(`  ✨ Este es el Banner #${realBannerIndex} (data-gtag-index="${gtagIndex}")`);
        } else {
          console.log(`  ⚠️ No se encontró data-gtag-index, usando índice secuencial #${i + 1}`);
        }

        // Obtener ID único del banner para detectar duplicados
        const bannerId = bannerClass.match(/default-carousel-([a-f0-9-]+)/)?.[1] || `banner-${loopIndex}`;
        const bannerKey = realBannerIndex !== null ? `gtag-${realBannerIndex}` : `id-${bannerId}`;

        if (!useIndicators) {
          if (processedBannerIds.has(bannerKey) || (realBannerIndex !== null && processedGtagIndexes.has(realBannerIndex))) {
            console.log(`  ⏭️ Banner ya procesado (carousel volvió al inicio), terminando análisis`);
            break;
          }
          processedBannerIds.add(bannerKey);
          if (realBannerIndex !== null) {
            processedGtagIndexes.add(realBannerIndex);
          }
        }

        // Actualizar el índice del banner con el índice real
        if (realBannerIndex !== null) {
          bannerResult.index = realBannerIndex;
          bannerResult.screenshot = `banner-${realBannerIndex}.png`;
        } else if (useIndicators && targetIndicatorIndex !== null) {
          bannerResult.index = targetIndicatorIndex + 1;
          bannerResult.screenshot = `banner-${targetIndicatorIndex + 1}.png`;
        }

        const screenshotIndex = realBannerIndex !== null
          ? realBannerIndex
          : (useIndicators && targetIndicatorIndex !== null ? targetIndicatorIndex + 1 : loopIndex);
        const screenshotFilename = `banner-${screenshotIndex}.png`;
        const screenshotPath = path.join(CONFIG.screenshotsDir, screenshotFilename);
        const ocrScreenshotPaths = [];
        const fallbackOcrPaths = [];

        try {
          await activeBanner.scrollIntoViewIfNeeded().catch(() => {});
          await page.waitForTimeout(250);
          await activeBanner.screenshot({ path: screenshotPath, timeout: 8000, scale: 'device' });
          fallbackOcrPaths.push(screenshotPath);
          console.log(`  📸 Screenshot guardado: ${screenshotFilename}`);
        } catch (screenshotError) {
          console.log(`  ⚠️ No se pudo capturar screenshot: ${screenshotError.message}`);
          const bannerBox = await activeBanner.boundingBox().catch(() => null);
          if (bannerBox) {
            const clip = {
              x: Math.max(0, bannerBox.x),
              y: Math.max(0, bannerBox.y),
              width: Math.max(1, bannerBox.width),
              height: Math.max(1, bannerBox.height),
            };
            try {
              await page.screenshot({ path: screenshotPath, clip, scale: 'device' });
              fallbackOcrPaths.push(screenshotPath);
              console.log(`  📸 Screenshot por recorte guardado: ${screenshotFilename}`);
            } catch (clipError) {
              console.log(`  ⚠️ No se pudo capturar screenshot por recorte: ${clipError.message}`);
            }
          }
        }

        const imageSrc = await bannerElement.locator('img').first().getAttribute('src').catch(() => null);
        if (imageSrc) {
          const sourceFilename = `banner-${screenshotIndex}-source.png`;
          const sourcePath = path.join(CONFIG.screenshotsDir, sourceFilename);
          const sourcePaths = await captureImageFromUrl(context, imageSrc, sourcePath);
          for (const pathItem of sourcePaths) {
            if (fs.existsSync(pathItem)) {
              ocrScreenshotPaths.push(pathItem);
            }
          }
          if (sourcePaths.length > 0) {
            bannerResult.screenshot = sourceFilename;
          }
        }

        const bannerImage = await activeBanner.locator('img').first();
        if (await bannerImage.count()) {
          await bannerImage.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
          await page.waitForTimeout(200);
          const imageFilename = realBannerIndex !== null
            ? `banner-${realBannerIndex}-img.png`
            : `banner-${loopIndex}-img.png`;
          const imagePath = path.join(CONFIG.screenshotsDir, imageFilename);
          try {
            await bannerImage.screenshot({ path: imagePath, timeout: 12000, scale: 'device' });
            fallbackOcrPaths.push(imagePath);
            console.log(`  🖼️ Screenshot de imagen guardado: ${imageFilename}`);
          } catch (imageError) {
            console.log(`  ⚠️ No se pudo capturar screenshot de imagen: ${imageError.message}`);
            const imageBox = await bannerImage.boundingBox().catch(() => null);
            if (imageBox) {
              const clip = {
                x: Math.max(0, imageBox.x),
                y: Math.max(0, imageBox.y),
                width: Math.max(1, imageBox.width),
                height: Math.max(1, imageBox.height),
              };
              try {
                await page.screenshot({ path: imagePath, clip, scale: 'device' });
                fallbackOcrPaths.push(imagePath);
                console.log(`  🖼️ Screenshot de imagen por recorte guardado: ${imageFilename}`);
              } catch (clipError) {
                console.log(`  ⚠️ No se pudo capturar recorte de imagen: ${clipError.message}`);
              }
            }
          }

          const bbox = await bannerImage.boundingBox().catch(() => null);
          if (bbox) {
            const cropHeight = Math.max(1, bbox.height * 0.45);
            const cropConfigs = [
              {
                label: 'top',
                y: Math.max(0, bbox.y),
              },
              {
                label: 'center',
                y: Math.max(0, bbox.y + (bbox.height - cropHeight) / 2),
              },
              {
                label: 'bottom',
                y: Math.max(0, bbox.y + bbox.height - cropHeight),
              },
            ];

            for (const config of cropConfigs) {
              const crop = {
                x: Math.max(0, bbox.x),
                y: config.y,
                width: Math.max(1, bbox.width),
                height: cropHeight,
              };
              const cropFilename = realBannerIndex !== null
                ? `banner-${realBannerIndex}-img-${config.label}.png`
                : `banner-${loopIndex}-img-${config.label}.png`;
              const cropPath = path.join(CONFIG.screenshotsDir, cropFilename);
              try {
                await page.screenshot({ path: cropPath, clip: crop, scale: 'device' });
                fallbackOcrPaths.push(cropPath);
                console.log(`  🧩 Screenshot de recorte guardado: ${cropFilename}`);
              } catch (cropError) {
                console.log(`  ⚠️ No se pudo capturar recorte de imagen: ${cropError.message}`);
              }
            }
          }
        }

        if (ocrScreenshotPaths.length === 0 && fallbackOcrPaths.length > 0) {
          ocrScreenshotPaths.push(...fallbackOcrPaths);
        }

        // Analizar TODOS los precios en el banner (incluye OCR si screenshot existe)
        const bannerPriceData = await analyzeBannerForPrices(
          page,
          bannerElement,
          ocrScreenshotPaths.length > 0 ? ocrScreenshotPaths : [screenshotPath]
        );
        const bannerPricesRaw = bannerPriceData.prices || [];
        const bannerPriceCounts = bannerPriceData.counts || {};
        bannerResult.bannerPricesRaw = bannerPricesRaw;
        bannerResult.bannerPriceCounts = bannerPriceCounts;
        bannerResult.bannerPrices = bannerPricesRaw;

        if (bannerPricesRaw.length === 0) {
          console.log(`  ℹ️ Banner sin precios detectados (posiblemente promocional)`);
          bannerResult.status = 'no_price';
          results.banners.push(bannerResult);

          const moved = await clickNextBanner(page, sliderRootSelector);
          if (!moved) {
            console.log('  ⚠️ No se pudo hacer click en siguiente');
          }
          continue;
        }

        // Obtener el link principal del banner (priorizar enlace del item)
        let href = null;
        const itemLink = await bannerElement.locator('a.carousel-item-link').first();
        if (await itemLink.count()) {
          href = await itemLink.getAttribute('href');
        }
        if (!href) {
          href = await getPrimaryBannerHref(bannerElement);
        }
        if (!href) {
          href = await bannerElement.locator('a').first().getAttribute('href');
        }

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
          await newPage.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: CONFIG.navigationTimeout });
          await newPage.waitForTimeout(2000);

          // Screenshot de la página de destino
          await newPage.screenshot({
            path: path.join(CONFIG.screenshotsDir, `banner-${loopIndex}-product.png`)
          });

          // Extraer TODOS los precios de la página de productos
          const productPrices = await extractProductPrices(newPage);
          bannerResult.productPrices = productPrices;

          if (productPrices.length === 0) {
            console.log(`  ⚠️ No se pudo extraer precios de la página de productos`);
            bannerResult.status = 'no_product_price';
            bannerResult.error = 'No se encontraron precios en la página de destino';
          } else {
            const filteredData = filterBannerPricesForComparison(
              bannerPricesRaw,
              bannerPriceCounts,
              productPrices
            );
            const bannerPrices = filteredData.filtered.length > 0
              ? filteredData.filtered
              : bannerPricesRaw;
            bannerResult.bannerPrices = bannerPrices;
            bannerResult.bannerPricesIgnored = filteredData.ignored;

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

      if (!useIndicators && i < totalBanners - 1) {
        try {
          // Verificar que la página sigue abierta antes de hacer click
          if (page.isClosed()) {
            console.log(`  🛑 Página cerrada, terminando análisis`);
            break;
          }

          const moved = await clickNextBanner(page, sliderRootSelector);
          if (!moved) {
            throw new Error('No se pudo avanzar con los selectores de navegación');
          }
          console.log(`  ➡️ Avanzando al siguiente banner...`);
          await page.waitForTimeout(2500); // Esperar animación del carousel (2.5s)
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
    const withPrice = results.banners.filter(b => b.bannerPrices && b.bannerPrices.length > 0).length;
    const noPrice = results.banners.filter(b => b.status === 'no_price').length;
    const matched = results.banners.filter(b => b.priceMatch === true).length;
    const mismatched = results.banners.filter(b => b.priceMatch === false).length;
    const errors = results.banners.filter(b => b.status === 'error').length;

    console.log(`\n📊 RESUMEN:`);
    console.log(`   Total banners analizados: ${total}`);
    console.log(`   🏷️  Con precio: ${withPrice}`);
    console.log(`   🚫 Sin precio: ${noPrice}`);
    console.log(`   ✅ Precios coinciden: ${matched}`);
    console.log(`   ❌ Precios NO coinciden: ${mismatched}`);
    if (errors > 0) {
      console.log(`   ⚠️  Errores: ${errors}`);
    }
  });
});
