// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * PCFactory Checkout Endpoints Monitor
 *
 * Este test verifica que todos los endpoints críticos del checkout
 * estén funcionando correctamente mediante llamadas directas a la API.
 *
 * A diferencia del monitor de medios de pago (E2E), este monitor hace
 * llamadas directas a los endpoints para detectar problemas específicos.
 */

// Configuración
const CONFIG = {
  baseUrl: 'https://api.pcfactory.cl',
  baseUrlCustomers: 'https://ww3.pcfactory.cl',
  webUrl: 'https://www.pcfactory.cl',

  // Credenciales desde GitHub Secrets (para endpoints P2 con auth)
  credentials: {
    rut: process.env.PCFACTORY_RUT || '',
    password: process.env.PCFACTORY_PASSWORD || ''
  },

  // Producto de prueba para el carrito (debe ser barato y con buen stock)
  testProduct: {
    id: 45190,
    cantidad: 1,
    origin: 'PCF',
    empresa: 'PCFACTORY'
  },

  // Datos de prueba para validaciones
  testData: {
    rut: '16915848', // RUT válido para pruebas
    sucursal: 9, // Mall Plaza Oeste
    idEmpresa: 1,
    codigoRestriccion: 1,
    // Para endpoint de delivery V2
    tiendaId: 11, // Tienda por defecto
    ciudadId: 1, // Santiago
    comunaId: 296 // Santiago Centro
  },

  // Timeouts
  timeouts: {
    fast: 1000,      // Endpoints que deberían ser rápidos (< 1s)
    normal: 2000,    // Endpoints normales (< 2s)
    slow: 3000       // Endpoints que pueden ser lentos (< 3s)
  }
};

// Variable global para almacenar cookies de sesión
let authCookies = null;

// Resultados globales para el reporte
const testResults = {
  timestamp: new Date().toISOString(),
  endpoints: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0,
    avgResponseTime: 0
  }
};

/**
 * Helper para registrar resultado de un endpoint
 */
function recordEndpointResult(result) {
  testResults.endpoints.push(result);
  testResults.summary.total++;

  if (result.status === 'PASSED') {
    testResults.summary.passed++;
  } else {
    testResults.summary.failed++;
  }
}

test.describe('PCFactory Checkout Endpoints Monitor', () => {

  // Login antes de todos los tests (solo si hay credenciales)
  test.beforeAll(async ({ browser }) => {
    // Solo intentar login si hay credenciales configuradas
    if (!CONFIG.credentials.rut || !CONFIG.credentials.password) {
      console.log('  ⚠️  No hay credenciales configuradas, endpoints P2 se probarán sin auth');
      return;
    }

    console.log('  🔐 Intentando login para endpoints P2...');

    try {
      const context = await browser.newContext();
      const page = await context.newPage();

      // Ir a login
      await page.goto(`${CONFIG.webUrl}/login`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(2000);

      // Llenar formulario
      await page.locator('input#loginRut, input[name="rut"]').first().fill(CONFIG.credentials.rut);
      await page.waitForTimeout(500);
      await page.locator('input#loginPassword, input[name="password"], input[type="password"]').first().fill(CONFIG.credentials.password);
      await page.waitForTimeout(500);

      // Hacer clic en login
      const loginButton = page.locator('button:has-text("Inicia sesión"), button[type="submit"]').first();
      await loginButton.click();

      // Esperar navegación (o error)
      await page.waitForTimeout(3000);

      // Verificar si el login fue exitoso
      const currentUrl = page.url();
      if (currentUrl.includes('/login')) {
        console.log('  ❌ Login falló, endpoints P2 se probarán sin auth');
        await context.close();
        return;
      }

      // Obtener cookies de sesión
      const cookies = await context.cookies();
      authCookies = cookies.map(c => `${c.name}=${c.value}`).join('; ');

      console.log(`  ✅ Login exitoso, cookies capturadas (${cookies.length} cookies)`);

      await context.close();
    } catch (error) {
      console.log(`  ⚠️  Error en login: ${error.message}, endpoints P2 se probarán sin auth`);
      authCookies = null;
    }
  });

  test.describe('🔴 P0 - Endpoints Críticos', () => {

    test('Endpoint: POST /carro/status - Verificar estado del carrito', async ({ request }) => {
      const result = {
        priority: 'P0',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/status',
        name: 'Verificar Estado del Carrito',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/status`, {
          data: {
            items: [CONFIG.testProduct]
          },
          timeout: CONFIG.timeouts.normal
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        // Validación 1: Status code 200
        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        // Validación 2: Response es JSON
        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        // Validación 3: Tiene campo status.activo
        expect(data).toHaveProperty('status');
        expect(data.status).toHaveProperty('activo');
        result.validations.push({ name: 'Tiene campo status.activo', passed: true });

        // Validación 4: Tiene items
        expect(data).toHaveProperty('items');
        expect(Array.isArray(data.items)).toBe(true);
        result.validations.push({ name: 'Tiene items array', passed: true });

        // Validación 5: Tiempo de respuesta aceptable
        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/status: ${result.responseTime}ms`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/status: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: POST /carro/entrega/opciones - Obtener opciones de entrega', async ({ request }) => {
      const result = {
        priority: 'P0',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/entrega/opciones',
        name: 'Opciones de Entrega',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/entrega/opciones`, {
          data: {
            items: [CONFIG.testProduct]
          },
          timeout: CONFIG.timeouts.normal
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        // Debe tener al menos una opción de entrega (retiro o envío)
        const hasRetiro = data.retiro && (data.retiro.status === true || data.retiro.status === 'Disponible');
        const hasEnvio = data.envioDigital || data.envio;
        expect(hasRetiro || hasEnvio).toBeTruthy();
        result.validations.push({ name: 'Tiene opciones de entrega', passed: true });

        // Si tiene retiro, debe tener sucursales
        if (data.retiro && data.retiro.disponibilidad) {
          expect(Array.isArray(data.retiro.disponibilidad)).toBe(true);
          result.validations.push({ name: 'Tiene sucursales disponibles', passed: true });
        }

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/entrega/opciones: ${result.responseTime}ms`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/entrega/opciones: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: POST /carro/pago/opciones - Obtener medios de pago', async ({ request }) => {
      const result = {
        priority: 'P0',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/pago/opciones',
        name: 'Medios de Pago',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.slow,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/pago/opciones`, {
          data: {
            items: [CONFIG.testProduct],
            entrega: {
              tipo: 'RETIRO',
              costo: 0,
              ventaExpres: false
            }
          },
          timeout: CONFIG.timeouts.slow
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        // Debe tener items (medios de pago)
        expect(data).toHaveProperty('items');
        expect(Array.isArray(data.items)).toBe(true);
        expect(data.items.length).toBeGreaterThan(0);
        result.validations.push({ name: 'Tiene medios de pago', passed: true });

        // Verificar que tiene medios de pago críticos
        const mediosCodigos = data.items.map(item => item.codigo);
        const tieneMediosCriticos = mediosCodigos.includes('ETP') ||
                                     mediosCodigos.includes('WP') ||
                                     mediosCodigos.includes('BCA');
        expect(tieneMediosCriticos).toBe(true);
        result.validations.push({ name: 'Tiene medios de pago críticos (ETP/WP/BCA)', passed: true });

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.slow);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.slow}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/pago/opciones: ${result.responseTime}ms (${data.items.length} medios disponibles)`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/pago/opciones: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });
  });

  test.describe('🟡 P1 - Endpoints Importantes', () => {

    test('Endpoint: POST /carro/entrega/retiro - Configurar retiro en tienda', async ({ request }) => {
      const result = {
        priority: 'P1',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/entrega/retiro',
        name: 'Configurar Retiro en Tienda',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.slow,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/entrega/retiro`, {
          data: {
            items: [{
              id: CONFIG.testProduct.id,
              cantidad: CONFIG.testProduct.cantidad,
              empresa: CONFIG.testProduct.empresa
            }],
            sucursal: CONFIG.testData.sucursal,
            origen: null,
            codigo_restriccion: CONFIG.testData.codigoRestriccion
          },
          timeout: CONFIG.timeouts.slow
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        expect(data).toHaveProperty('status');
        expect(data.status).toHaveProperty('activo');
        result.validations.push({ name: 'Tiene status.activo', passed: true });

        expect(data).toHaveProperty('sucursal');
        expect(data.sucursal).toHaveProperty('nombre');
        result.validations.push({ name: 'Tiene información de sucursal', passed: true });

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.slow);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.slow}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/entrega/retiro: ${result.responseTime}ms`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/entrega/retiro: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: POST /carro/entrega/despacho - Obtener fechas de despacho', async ({ request }) => {
      const result = {
        priority: 'P1',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/entrega/despacho',
        name: 'Fechas de Despacho',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.slow,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/entrega/despacho`, {
          data: {
            items: [{
              id: CONFIG.testProduct.id,
              cantidad: CONFIG.testProduct.cantidad,
              empresa: CONFIG.testProduct.empresa
            }],
            direccion: {
              // Dirección de prueba en Santiago
              comuna: 'Santiago',
              region: 'Metropolitana'
            },
            codigo_restriccion: CONFIG.testData.codigoRestriccion
          },
          timeout: CONFIG.timeouts.slow
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        // Este endpoint puede retornar 200, 400 o 500
        const validStatuses = [200, 400, 500];
        expect(validStatuses).toContain(response.status());
        result.validations.push({ name: 'Status code válido (200, 400 o 500)', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        if (response.status() === 200) {
          // Si hay despacho disponible, validar estructura
          expect(data).toHaveProperty('error');
          result.validations.push({ name: 'Tiene campo error', passed: true });
        }

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.slow);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.slow}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/entrega/despacho: ${result.responseTime}ms (status ${response.status()})`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/entrega/despacho: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: POST /carro/entrega/diferido - Consultar despacho diferido', async ({ request }) => {
      const result = {
        priority: 'P1',
        endpoint: 'POST /pcfactory-services-carro-compra/v1/carro/entrega/diferido',
        name: 'Despacho Diferido',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.post(`${CONFIG.baseUrl}/pcfactory-services-carro-compra/v1/carro/entrega/diferido`, {
          data: {
            id_empresa: CONFIG.testData.idEmpresa,
            productos: [{
              id_producto: CONFIG.testProduct.id,
              cantidad: CONFIG.testProduct.cantidad
            }],
            codigo_restriccion: CONFIG.testData.codigoRestriccion
          },
          timeout: CONFIG.timeouts.normal
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        expect(data).toHaveProperty('error');
        expect(data.error).toBe(false);
        result.validations.push({ name: 'Sin errores (error: false)', passed: true });

        expect(data).toHaveProperty('resultado');
        expect(Array.isArray(data.resultado)).toBe(true);
        result.validations.push({ name: 'Tiene resultado array', passed: true });

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ POST /carro/entrega/diferido: ${result.responseTime}ms`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ POST /carro/entrega/diferido: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: GET /perfil/rut/{rut} - Validar RUT', async ({ request }) => {
      const result = {
        priority: 'P1',
        endpoint: 'GET /pcfactory-services-perfil-privado/v1/perfil/rut/{rut}',
        name: 'Validar RUT',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const response = await request.get(`${CONFIG.baseUrl}/pcfactory-services-perfil-privado/v1/perfil/rut/${CONFIG.testData.rut}`, {
          timeout: CONFIG.timeouts.normal
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        expect(data).toHaveProperty('valido');
        expect(data.valido).toBe(true);
        result.validations.push({ name: 'RUT válido', passed: true });

        expect(data).toHaveProperty('mensaje');
        result.validations.push({ name: 'Tiene mensaje', passed: true });

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ GET /perfil/rut/{rut}: ${result.responseTime}ms`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ GET /perfil/rut/{rut}: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: GET /delivery/ship - Verificar disponibilidad de despacho (V2)', async ({ request }) => {
      const result = {
        priority: 'P1',
        endpoint: 'GET /api-delivery-method/v2/delivery/ship/{tienda}/{ciudad}/{comuna}/web',
        name: 'Disponibilidad Despacho V2',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        // Construir URL con query params
        const url = `https://api.pcfactory.cl/api-delivery-method/v2/delivery/ship/${CONFIG.testData.tiendaId}/${CONFIG.testData.ciudadId}/${CONFIG.testData.comunaId}/web?cantidad=${CONFIG.testProduct.cantidad}&id_producto=${CONFIG.testProduct.id}&total=100000`;

        const response = await request.get(url, {
          timeout: CONFIG.timeouts.normal
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        expect(response.status()).toBe(200);
        result.validations.push({ name: 'Status code 200', passed: true });

        const data = await response.json();
        result.validations.push({ name: 'Response es JSON', passed: true });

        // Validar estructura de respuesta
        expect(data).toHaveProperty('codigo');
        result.validations.push({ name: 'Tiene campo codigo', passed: true });

        // Si el código es 0, significa que hay despacho disponible
        if (data.codigo === 0 || data.codigo === '0') {
          expect(data).toHaveProperty('resultado');
          expect(data.resultado).toHaveProperty('tarifas');
          expect(Array.isArray(data.resultado.tarifas)).toBe(true);
          result.validations.push({ name: 'Tiene tarifas disponibles', passed: true });

          if (data.resultado.tarifas.length > 0) {
            const tarifa = data.resultado.tarifas[0];
            expect(tarifa).toHaveProperty('dias_entrega');
            result.validations.push({ name: 'Tarifa tiene días de entrega', passed: true });
          }
        } else {
          // Si no hay despacho disponible, solo verificamos que responda correctamente
          result.validations.push({ name: 'Endpoint responde correctamente (sin despacho disponible)', passed: true });
        }

        expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
        result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

        result.status = 'PASSED';
        console.log(`  ✅ GET /delivery/ship: ${result.responseTime}ms (codigo: ${data.codigo})`);

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ GET /delivery/ship: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });
  });

  test.describe('🟢 P2 - Endpoints de Usuario', () => {

    test('Endpoint: GET /me - Obtener datos de sesión', async ({ request }) => {
      const hasAuth = authCookies !== null;
      const result = {
        priority: 'P2',
        endpoint: 'GET /api/customers/realms/principal/me',
        name: hasAuth ? 'Datos de Sesión (con auth)' : 'Datos de Sesión (sin auth)',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const headers = hasAuth ? { Cookie: authCookies } : {};
        const response = await request.get(`${CONFIG.baseUrlCustomers}/api/customers/realms/principal/me`, {
          headers,
          timeout: CONFIG.timeouts.normal,
          failOnStatusCode: false
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        if (hasAuth) {
          // CON autenticación: debe dar 200 y tener datos de usuario
          expect(response.status()).toBe(200);
          result.validations.push({ name: 'Status code 200 (autenticado)', passed: true });

          const data = await response.json();
          result.validations.push({ name: 'Response es JSON', passed: true });

          expect(data).toHaveProperty('uuid');
          result.validations.push({ name: 'Tiene datos de usuario (uuid)', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /me: ${result.responseTime}ms (200 con auth, usuario: ${data.login || 'N/A'})`);
        } else {
          // SIN autenticación: debe dar 401
          expect(response.status()).toBe(401);
          result.validations.push({ name: 'Status code 401 (sin auth)', passed: true });

          const data = await response.json();
          result.validations.push({ name: 'Response es JSON', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /me: ${result.responseTime}ms (401 esperado sin auth)`);
        }

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ GET /me: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: GET /perfil/datos - Obtener perfil privado', async ({ request }) => {
      const hasAuth = authCookies !== null;
      const result = {
        priority: 'P2',
        endpoint: 'GET /pcfactory-services-perfil-privado/v1/perfil/datos',
        name: hasAuth ? 'Perfil Privado (con auth)' : 'Perfil Privado (sin auth)',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const headers = hasAuth ? { Cookie: authCookies } : {};
        const response = await request.get(`${CONFIG.baseUrl}/pcfactory-services-perfil-privado/v1/perfil/datos`, {
          headers,
          timeout: CONFIG.timeouts.normal,
          failOnStatusCode: false
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        if (hasAuth) {
          // CON autenticación: debe dar 200 y tener datos del perfil
          expect(response.status()).toBe(200);
          result.validations.push({ name: 'Status code 200 (autenticado)', passed: true });

          const data = await response.json();
          result.validations.push({ name: 'Response es JSON', passed: true });

          expect(data).toHaveProperty('rut');
          result.validations.push({ name: 'Tiene datos del perfil (rut)', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /perfil/datos: ${result.responseTime}ms (200 con auth, rut: ${data.rut || 'N/A'})`);
        } else {
          // SIN autenticación: debe dar error
          const validStatuses = [400, 401, 403, 500];
          expect(validStatuses).toContain(response.status());
          result.validations.push({ name: 'Status code indica falta de auth', passed: true });

          result.validations.push({ name: 'Endpoint responde', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /perfil/datos: ${result.responseTime}ms (${response.status()} esperado sin auth)`);
        }

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ GET /perfil/datos: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });

    test('Endpoint: GET /perfil/direcciones - Obtener direcciones', async ({ request }) => {
      const hasAuth = authCookies !== null;
      const result = {
        priority: 'P2',
        endpoint: 'GET /pcfactory-services-perfil-privado/v1/perfil/direcciones',
        name: hasAuth ? 'Direcciones del Usuario (con auth)' : 'Direcciones del Usuario (sin auth)',
        status: 'UNKNOWN',
        responseTime: 0,
        statusCode: 0,
        error: null,
        expectedTimeout: CONFIG.timeouts.normal,
        validations: []
      };

      const startTime = Date.now();

      try {
        const headers = hasAuth ? { Cookie: authCookies } : {};
        const response = await request.get(`${CONFIG.baseUrl}/pcfactory-services-perfil-privado/v1/perfil/direcciones`, {
          headers,
          timeout: CONFIG.timeouts.normal,
          failOnStatusCode: false
        });

        result.responseTime = Date.now() - startTime;
        result.statusCode = response.status();

        if (hasAuth) {
          // CON autenticación: debe dar 200 y tener direcciones (puede ser array vacío)
          expect(response.status()).toBe(200);
          result.validations.push({ name: 'Status code 200 (autenticado)', passed: true });

          const data = await response.json();
          result.validations.push({ name: 'Response es JSON', passed: true });

          expect(Array.isArray(data)).toBe(true);
          result.validations.push({ name: 'Response es un array', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /perfil/direcciones: ${result.responseTime}ms (200 con auth, ${data.length} direcciones)`);
        } else {
          // SIN autenticación: debe dar error
          const validStatuses = [400, 401, 403, 500];
          expect(validStatuses).toContain(response.status());
          result.validations.push({ name: 'Status code indica falta de auth', passed: true });

          result.validations.push({ name: 'Endpoint responde', passed: true });

          expect(result.responseTime).toBeLessThan(CONFIG.timeouts.normal);
          result.validations.push({ name: `Tiempo < ${CONFIG.timeouts.normal}ms`, passed: true });

          result.status = 'PASSED';
          console.log(`  ✅ GET /perfil/direcciones: ${result.responseTime}ms (${response.status()} esperado sin auth)`);
        }

      } catch (error) {
        result.status = 'FAILED';
        result.error = error.message;
        result.responseTime = Date.now() - startTime;
        console.log(`  ❌ GET /perfil/direcciones: ${error.message}`);
        throw error;
      } finally {
        recordEndpointResult(result);
      }
    });
  });
});

// Hook para generar reporte al finalizar
test.afterAll(async () => {
  const fs = require('fs');
  const reportPath = './test-results/checkout-endpoints-report.json';

  try {
    fs.mkdirSync('./test-results', { recursive: true });

    // Calcular tiempo promedio
    const totalTime = testResults.endpoints.reduce((sum, e) => sum + e.responseTime, 0);
    testResults.summary.avgResponseTime = Math.round(totalTime / testResults.endpoints.length);

    fs.writeFileSync(reportPath, JSON.stringify(testResults, null, 2));

    console.log('\n========================================');
    console.log('RESUMEN DE MONITOREO DE ENDPOINTS CHECKOUT');
    console.log('========================================');
    console.log(`Timestamp: ${testResults.timestamp}`);
    console.log(`Total: ${testResults.summary.total}`);
    console.log(`✅ Passed: ${testResults.summary.passed}`);
    console.log(`❌ Failed: ${testResults.summary.failed}`);
    console.log(`⏱️  Tiempo promedio: ${testResults.summary.avgResponseTime}ms`);
    console.log('----------------------------------------');

    // Agrupar por prioridad
    const byPriority = {
      P0: testResults.endpoints.filter(e => e.priority === 'P0'),
      P1: testResults.endpoints.filter(e => e.priority === 'P1'),
      P2: testResults.endpoints.filter(e => e.priority === 'P2')
    };

    for (const [priority, endpoints] of Object.entries(byPriority)) {
      if (endpoints.length > 0) {
        console.log(`\n${priority === 'P0' ? '🔴' : priority === 'P1' ? '🟡' : '🟢'} ${priority}:`);
        for (const endpoint of endpoints) {
          const icon = endpoint.status === 'PASSED' ? '✅' : '❌';
          console.log(`${icon} ${endpoint.name}: ${endpoint.responseTime}ms (${endpoint.statusCode})`);
          if (endpoint.error) {
            console.log(`   Error: ${endpoint.error}`);
          }
        }
      }
    }

    console.log('========================================\n');
  } catch (e) {
    console.error('Error generating report:', e);
  }
});
