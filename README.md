# PCFactory Monitor - Fix v5

## Cambios incluidos

### 1. Hora Chile en todos los dashboards
Todos los timestamps ahora muestran hora Chile (UTC-3) en vez de UTC.
Formato: `DD/MM/YYYY HH:MM:SS Chile`

### 2. Workflow corregido (monitor.yml)
- **Ventana ampliada**: De 10 a 20 minutos para compensar delays de GitHub Actions
- **Hora 01 UTC agregada**: Para cubrir 10pm Chile (01:00 UTC del día siguiente)
- Horarios finales: 01:00, 12:00, 17:00, 23:00 UTC (10pm, 9am, 2pm, 8pm Chile)

### 3. Nueva tabla de todas las categorías (monitor.py)
- Se agregó una sección "Todas las Categorías" con filtro de búsqueda
- Muestra: ID, Nombre, Status HTTP, Cantidad de productos, Enlace
- Las categorías vacías y con error se destacan con colores

### 4. Se preservó todo lo original
- Isotipo de PCFactory ✓
- Cards detalladas de medios de pago (uptime 24h, duración, gateway) ✓
- Lógica de parsing de Playwright en login ✓
- Todos los estilos y funcionalidades originales ✓

## Archivos a reemplazar

```
.github/workflows/monitor.yml      ← REEMPLAZAR
monitor.py                         ← REEMPLAZAR  
delivery_monitor.py                ← REEMPLAZAR
payment_dashboard.py               ← REEMPLAZAR
login/scripts/login_dashboard.py   ← REEMPLAZAR
```

## Instalación

1. Descomprime el ZIP
2. Copia los archivos a tu repositorio reemplazando los existentes
3. Commit y push
4. Ejecuta manualmente con `run_payments: true` y `run_login: true` para probar
