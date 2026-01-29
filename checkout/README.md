# 🔌 Monitor de Endpoints del Checkout - PCFactory

Monitor automatizado que verifica el estado de los endpoints críticos del flujo de checkout de PCFactory mediante llamadas directas a la API.

## 📋 Descripción

Este monitor hace llamadas directas a los endpoints de API del checkout para verificar:
- ✅ Disponibilidad (uptime)
- ⏱️ Tiempos de respuesta
- 📊 Estructura de respuestas
- 🔍 Validaciones de datos

A diferencia del monitor de medios de pago (E2E), este monitor **no navega por la UI** sino que hace **llamadas directas a los endpoints**, lo que permite:
- Detección más rápida de problemas
- Identificación exacta del endpoint con fallo
- Mayor estabilidad (no depende de la UI)
- Mejor para alertas automatizadas

## 🎯 Endpoints Monitoreados

### 🔴 Prioridad 0 - Críticos (bloquean checkout)
1. **POST /carro/status** - Verificar estado del carrito
2. **POST /carro/entrega/opciones** - Obtener opciones de entrega
3. **POST /carro/pago/opciones** - Obtener medios de pago

### 🟡 Prioridad 1 - Importantes (afectan UX)
4. **POST /carro/entrega/retiro** - Configurar retiro en tienda
5. **POST /carro/entrega/despacho** - Obtener fechas de despacho
6. **POST /carro/entrega/diferido** - Consultar despacho diferido
7. **GET /perfil/rut/{rut}** - Validar RUT
8. **GET /delivery/ship** - Verificar disponibilidad de despacho (API V2)

### 🟢 Prioridad 2 - Secundarios (usuario con auth)
9. **GET /me** - Obtener datos de sesión
10. **GET /perfil/datos** - Obtener datos del perfil
11. **GET /perfil/direcciones** - Obtener direcciones del usuario

**Nota:** Los endpoints P2 requieren autenticación. Si se configuran las credenciales en GitHub Secrets (`PCFACTORY_RUT` y `PCFACTORY_PASSWORD`), el monitor hará login automáticamente y probará estos endpoints con datos reales. Si no hay credenciales, solo verificará que rechacen correctamente las peticiones sin auth.

## 🚀 Instalación

```bash
# Instalar dependencias
npm install

# Instalar navegadores de Playwright (opcional, ya que este monitor usa API)
npx playwright install
```

## 📊 Uso

### Ejecutar el monitor

```bash
# Ejecutar tests
npm test

# Ejecutar con UI de Playwright
npm run test:ui

# Ver reporte HTML de Playwright
npm run report
```

### Ver el dashboard

**IMPORTANTE:** El dashboard necesita un servidor HTTP para funcionar correctamente. No abras `dashboard.html` directamente (file://) porque el navegador bloqueará las peticiones por seguridad.

**Opción 1: Usar el servidor integrado (Recomendado)**

```bash
# Servir el dashboard
npm run dashboard

# Se abrirá en: http://localhost:8080
```

**Opción 2: Usar Python**

```bash
# Python 3
python3 -m http.server 8080

# Python 2
python -m SimpleHTTPServer 8080

# Luego abre: http://localhost:8080/dashboard.html
```

**Opción 3: Usar npx http-server**

```bash
npx http-server -p 8080
# Abre: http://localhost:8080/dashboard.html
```

El dashboard se actualiza automáticamente cada 30 segundos.

## 📈 Reportes

Los resultados se guardan en:
- `test-results/checkout-endpoints-report.json` - Reporte JSON con resultados detallados
- `test-results/html-report/` - Reporte HTML de Playwright
- `dashboard.html` - Dashboard visual con estado de endpoints

### Estructura del reporte JSON

```json
{
  "timestamp": "2026-01-29T...",
  "endpoints": [
    {
      "priority": "P0",
      "endpoint": "POST /carro/status",
      "name": "Verificar Estado del Carrito",
      "status": "PASSED",
      "responseTime": 419,
      "statusCode": 200,
      "validations": [
        { "name": "Status code 200", "passed": true },
        { "name": "Tiene campo status.activo", "passed": true }
      ]
    }
  ],
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "avgResponseTime": 450
  }
}
```

## 🔧 Configuración

### Credenciales para endpoints P2 (opcional)

Los endpoints P2 (perfil, direcciones, datos de sesión) requieren autenticación. Si quieres probarlos con datos reales:

**Localmente:**
```bash
export PCFACTORY_RUT="tu-rut"
export PCFACTORY_PASSWORD="tu-password"
npm test
```

**GitHub Actions:**
Configura estos secretos en tu repositorio:
- `PCFACTORY_RUT`
- `PCFACTORY_PASSWORD`

Si no hay credenciales, el monitor solo verificará que estos endpoints rechacen correctamente peticiones sin auth.

### Modificar el producto de prueba

En `tests/checkout-endpoints.spec.js`:

```javascript
const CONFIG = {
  testProduct: {
    id: 45190,      // ID del producto
    cantidad: 1,
    origin: 'PCF',
    empresa: 'PCFACTORY'
  }
};
```

### Ajustar timeouts

```javascript
const CONFIG = {
  timeouts: {
    fast: 1000,      // Endpoints rápidos (< 1s)
    normal: 2000,    // Endpoints normales (< 2s)
    slow: 3000       // Endpoints lentos (< 3s)
  }
};
```

## 🤖 Integración con CI/CD

### GitHub Actions

Ejemplo de workflow:

```yaml
name: Checkout Endpoints Monitor

on:
  schedule:
    - cron: '*/15 * * * *'  # Cada 15 minutos
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd checkout
          npm ci

      - name: Run monitor
        run: |
          cd checkout
          npm test

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: checkout-endpoints-results
          path: |
            checkout/test-results/
            checkout/dashboard.html
```

## 📊 Métricas

Para cada endpoint se mide:
- ✅ **Status Code**: Si responde con el código esperado
- ⏱️ **Response Time**: Tiempo de respuesta en milisegundos
- 📋 **Validaciones**: Estructura de datos correcta
- 🔄 **Uptime**: Porcentaje de disponibilidad

## 🚨 Alertas

Los endpoints se clasifican por prioridad:
- **P0 (🔴 Críticos)**: Bloquean el checkout completamente
- **P1 (🟡 Importantes)**: Afectan UX pero no bloquean
- **P2 (🟢 Secundarios)**: Opcionales o de usuario

Las alertas deben configurarse priorizando los P0.

## 🔍 Troubleshooting

### El test falla con "timeout exceeded"
- Aumenta el timeout en `playwright.config.js`
- Verifica tu conexión a internet
- Revisa si la API de PCFactory está respondiendo lentamente

### El test falla con "401 Unauthorized"
- Los endpoints de usuario (P2) requieren autenticación
- El test verifica que respondan con 401 cuando no hay auth (esperado)

### El dashboard no carga
- Ejecuta primero `npm test` para generar el reporte
- Verifica que existe `test-results/checkout-endpoints-report.json`

## 📝 Notas

- Este monitor NO crea órdenes reales
- Solo verifica disponibilidad y tiempos de respuesta de la API
- Los endpoints de usuario (P2) se verifican sin autenticación (esperan 401)

## 🤝 Contribuir

Para agregar nuevos endpoints al monitor:

1. Agrega el endpoint a `tests/checkout-endpoints.spec.js`
2. Define las validaciones apropiadas
3. Clasifica la prioridad (P0, P1, P2)
4. Actualiza esta documentación
