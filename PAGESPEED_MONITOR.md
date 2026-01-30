# ⚡ Monitor de PageSpeed - Core Web Vitals

Monitor de performance web usando Google PageSpeed Insights API para medir Core Web Vitals de PCFactory.cl

## 📊 Métricas Monitoreadas

### Core Web Vitals (Google)
- **LCP** (Largest Contentful Paint) - Tiempo de carga del contenido principal
  - Bueno: < 2.5s
  - Mejorable: 2.5s - 4.0s
  - Pobre: > 4.0s

- **FID** (First Input Delay) - Tiempo de respuesta a primera interacción
  - Bueno: < 100ms
  - Mejorable: 100ms - 300ms
  - Pobre: > 300ms

- **CLS** (Cumulative Layout Shift) - Estabilidad visual
  - Bueno: < 0.1
  - Mejorable: 0.1 - 0.25
  - Pobre: > 0.25

### Otras Métricas
- Performance Score (0-100)
- FCP (First Contentful Paint)
- TTI (Time to Interactive)
- Speed Index
- TBT (Total Blocking Time)

### Scores Adicionales
- Accessibility Score
- Best Practices Score
- SEO Score

## 🚀 Uso

### Localmente

```bash
# Ejecutar monitor
python pagespeed_monitor.py --output-dir ./output

# Generar dashboard
python pagespeed_dashboard.py --results ./output/pagespeed_report.json --output-dir ./output

# Ver dashboard
open output/pagespeed.html
```

### Con API Key (recomendado para más requests)

```bash
# Obtén tu API key en: https://developers.google.com/speed/docs/insights/v5/get-started
python pagespeed_monitor.py --api-key YOUR_API_KEY --output-dir ./output
```

## 📁 Archivos Generados

- `pagespeed_report.json` - Reporte completo de la última ejecución
- `pagespeed_history.json` - Historial de mediciones (hasta 90 días)
- `pagespeed.html` - Dashboard visual con gráficos

## ⏰ Frecuencia

- **GitHub Actions**: Una vez al día a las 15:00 UTC (12pm Chile)
- **Local**: Ejecutar manualmente cuando sea necesario

## 📈 Dashboard

El dashboard incluye:
- Métricas actuales Mobile y Desktop
- Indicadores de estado Core Web Vitals (Bueno/Mejorable/Pobre)
- Gráficos de evolución temporal (últimos 30 días)
- Performance Score histórico
- Comparación Mobile vs Desktop

## 🔗 Links

- **Dashboard en vivo**: https://aincatoni.github.io/pcfactory-monitor/pagespeed.html
- **PageSpeed Insights API**: https://developers.google.com/speed/docs/insights/v5/about
- **Core Web Vitals**: https://web.dev/vitals/

## ⚠️ Limitaciones

- Sin API key: 25 requests/día
- Con API key: Depende del plan de Google Cloud
- Cada ejecución hace 2 requests (mobile + desktop)

## 💡 Notas

- Los valores pueden variar entre ejecuciones debido a condiciones de red
- Google recomienda promediar múltiples mediciones
- El historial se mantiene automáticamente (últimos 90 días)
