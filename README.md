# PCFactory Monitor

## Qué hace este repo
Este proyecto ejecuta varios monitores automáticos sobre pc Factory y publica dashboards en GitHub Pages. Cada monitor valida un área crítica del sitio y deja reportes y capturas para revisión.

## Monitores disponibles

### 1) Categorías
Verifica el estado de las categorías principales:
- Revisa disponibilidad (HTTP/status) y cantidad de productos.
- Detecta categorías vacías o con errores.
- Genera historial y un dashboard con tabla completa.

### 2) Despacho / Delivery
Simula búsquedas de despacho con producto + total y valida:
- Disponibilidad de envío por ciudad/comuna.
- Respuestas del backend y posibles errores.
- Genera un dashboard con resultados y tendencias.

### 3) Medios de pago
Ejecuta pruebas con Playwright para verificar:
- Disponibilidad de medios de pago.
- Respuesta de gateways y consistencia de la UI.
- Dashboard con uptime y detalle de fallos.

### 4) Login
Prueba el flujo de inicio de sesión:
- Valida formulario, autenticación y accesos.
- Guarda evidencia (videos) cuando hay fallos.
- Dashboard con el estado del login.

### 5) Banners (precios y links)
Analiza el slider principal:
- Detecta precios en banners (OCR + texto).
- Compara contra precios reales en páginas destino.
- Genera capturas por banner y dashboard con estado.

### 6) Checkout
Valida endpoints clave del checkout:
- Detecta errores en pasos críticos del flujo.
- Reporta resultados en dashboard.

## Dashboards
Los resultados se publican en GitHub Pages:
- `index.html` (resumen general)
- `banners.html`, `payments.html`, `login.html`, `checkout.html`, etc.

## Cómo correr manualmente en GitHub Actions
En Actions → PCFactory Monitor → Run workflow:
- `run_payments`, `run_login`, `run_banners` para habilitar monitores puntuales.
- `run_only_banners` para ejecutar SOLO banners y actualizar el dashboard.
