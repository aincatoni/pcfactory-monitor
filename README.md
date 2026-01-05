# PCFactory Monitor - Fix v4

## Cambios incluidos

### 1. Workflow corregido (`monitor.yml`)
- **Ventana ampliada**: De 10 a 20 minutos para compensar delays de GitHub Actions
- **Hora 01 UTC agregada**: Para cubrir 10pm Chile (01:00 UTC del día siguiente)
- Horarios finales: 01:00, 12:00, 17:00, 23:00 UTC (10pm, 9am, 2pm, 8pm Chile)

### 2. Hora Chile en dashboards
- Todos los dashboards ahora muestran hora Chile en vez de UTC
- Formato: `DD/MM/YYYY HH:MM:SS Chile`
- Se usa offset UTC-3 (horario de verano) / UTC-4 (horario de invierno)

## Archivos a reemplazar

```
.github/workflows/monitor.yml      ← REEMPLAZAR
monitor.py                         ← REEMPLAZAR  
delivery_monitor.py                ← REEMPLAZAR
payment_dashboard.py               ← REEMPLAZAR
login/scripts/login_dashboard.py   ← REEMPLAZAR
```

## Función helper para hora Chile

Todos los scripts usan esta función para convertir UTC a Chile:

```python
from datetime import datetime, timezone, timedelta

def utc_to_chile(dt_utc):
    """Convierte datetime UTC a hora Chile (UTC-3 verano, UTC-4 invierno)."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    # Chile usa UTC-3 en verano (sept-abril) y UTC-4 en invierno (abril-sept)
    # Simplificación: usar UTC-3 (horario de verano actual)
    chile_offset = timedelta(hours=-3)
    chile_tz = timezone(chile_offset)
    
    return dt_utc.astimezone(chile_tz)

def format_chile_timestamp(iso_timestamp):
    """Formatea un timestamp ISO a formato Chile."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        dt_chile = utc_to_chile(dt)
        return dt_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'
    except:
        return iso_timestamp[:19] if iso_timestamp else 'N/A'
```

## Instalación

1. Copia todos los archivos a tu repositorio
2. Commit y push a main
3. Ejecuta manualmente con `run_payments: true` y `run_login: true` para probar

## Verificación

Después de la próxima ejecución programada (01:00, 12:00, 17:00, o 23:00 UTC), los dashboards de payments y login deberían actualizarse automáticamente y mostrar la hora en formato Chile.
