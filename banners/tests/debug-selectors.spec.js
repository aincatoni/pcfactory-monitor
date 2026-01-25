// @ts-check
const { test } = require('@playwright/test');
const fs = require('fs');

/**
 * Script de diagnóstico para encontrar el selector correcto del slider principal
 */

test('Diagnosticar selectores del slider principal', async ({ page }) => {
  console.log('🔍 Diagnóstico de selectores de slider...\n');

  // Navegar a homepage
  await page.goto('https://www.pcfactory.cl', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Capturar screenshot completo
  await page.screenshot({
    path: 'test-results/homepage-full.png',
    fullPage: false
  });
  console.log('📸 Screenshot completo guardado\n');

  // Probar diferentes selectores
  const selectorsToTest = [
    '.swiper-slide',
    '.carousel-item',
    '[class*="Carousel"]',
    '[class*="Banner"]',
    '[class*="banner"]',
    '[class*="slider"]',
    '[class*="Slider"]',
    '[class*="slide"]',
    '.slick-slide',
    '[data-slide]',
    '[class*="hero"]',
    '[class*="Hero"]',
    'picture',
    'picture img',
    // Más específicos
    '.swiper-container .swiper-slide',
    '[class*="MainCarousel"]',
    '[class*="mainSlider"]',
  ];

  console.log('Probando selectores:\n');

  for (const selector of selectorsToTest) {
    try {
      const elements = await page.locator(selector).all();
      if (elements.length > 0) {
        console.log(`✅ ${selector}: ${elements.length} elementos encontrados`);

        // Capturar screenshot del primer elemento
        try {
          const firstElement = elements[0];
          await firstElement.screenshot({
            path: `test-results/selector-${selector.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
            timeout: 3000
          });
        } catch (e) {
          // No importa si falla el screenshot
        }
      }
    } catch (e) {
      // Selector no válido o no encontrado
    }
  }

  // Obtener clases de elementos en la parte superior de la página
  console.log('\n\n🔍 Analizando estructura HTML del área superior:\n');

  const topElements = await page.evaluate(() => {
    const elements = [];
    // Buscar elementos grandes en la parte superior (probables sliders)
    const allElements = document.querySelectorAll('*');

    for (const el of allElements) {
      const rect = el.getBoundingClientRect();
      // Si el elemento está en la parte superior y es grande
      if (rect.top < 600 && rect.width > 500 && rect.height > 200) {
        elements.push({
          tag: el.tagName,
          classes: Array.from(el.classList),
          id: el.id,
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          top: Math.round(rect.top)
        });
      }
    }

    return elements;
  });

  console.log('Elementos grandes en área superior:');
  topElements.forEach(el => {
    console.log(`  - <${el.tag}> ${el.classes.length > 0 ? '.' + el.classes.join('.') : ''} ${el.id ? '#' + el.id : ''}`);
    console.log(`    Tamaño: ${el.width}x${el.height}px, Top: ${el.top}px`);
  });

  console.log('\n✅ Diagnóstico completado. Revisa los screenshots en test-results/');
});
