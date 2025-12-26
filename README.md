# 🖥️ PCFactory Monitor

Monitoreo automático de **categorías** y **despachos** de PCFactory que se ejecuta cada 10 minutos y genera dashboards públicos.

![Dashboard Preview](https://img.shields.io/badge/status-live-brightgreen)

## 📊 Dashboards

| Monitor | Descripción |
|---------|-------------|
| **Categorías** | Verifica que todas las categorías tengan productos y URLs accesibles |
| **Despacho RM** | Monitorea disponibilidad y días de entrega a las 52 comunas de la Región Metropolitana |

## 🚀 Cómo configurar

### 1. Crear repositorio en GitHub

1. Ve a [github.com/new](https://github.com/new)
2. Nombre: `pcfactory-monitor`
3. Selecciona **Public** (necesario para GitHub Pages gratis)
4. Click en "Create repository"

### 2. Subir los archivos

```bash
# Clona el repo vacío
git clone https://github.com/TU_USUARIO/pcfactory-monitor.git
cd pcfactory-monitor

# Copia los archivos del monitor aquí:
# - monitor.py (categorías)
# - delivery_monitor.py (despachos)
# - requirements.txt
# - .github/workflows/monitor.yml

# Sube los cambios
git add .
git commit -m "Initial commit - PCFactory monitor"
git push origin main
```

### 3. Habilitar GitHub Pages

1. Ve a tu repositorio en GitHub
2. Click en **Settings** (⚙️)
3. En el menú lateral, click en **Pages**
4. En "Build and deployment", selecciona: **GitHub Actions**

### 4. Configurar producto para Delivery Monitor

Por defecto usa producto `53880`. Para cambiarlo:

1. Ve a **Actions** → **PCFactory Monitor**
2. Click en **Run workflow**
3. Ingresa el ID del producto y total

O modifica los valores por defecto en `.github/workflows/monitor.yml`:
```yaml
inputs:
  producto:
    default: '53880'  # Cambia esto
  total:
    default: '554990'  # Cambia esto
```

### 5. Ver los dashboards

Una vez que el workflow corra, tus dashboards estarán en:
```
https://TU_USUARIO.github.io/pcfactory-monitor/          # Categorías
https://TU_USUARIO.github.io/pcfactory-monitor/delivery.html  # Despacho RM
```

## 📦 Qué incluye cada dashboard

### Dashboard de Categorías
- **Health Score**: Porcentaje de categorías con productos
- **Total categorías**: Número total de categorías
- **URLs OK/Error**: Estado de las URLs
- **Categorías vacías**: Lista de categorías sin productos

### Dashboard de Despacho RM
- **Cobertura**: Porcentaje de comunas con despacho disponible
- **Promedio días**: Tiempo promedio de entrega
- **Distribución por días**: Gráfico de barras de días de entrega
- **Comunas sin despacho**: Lista de comunas problemáticas
- **Tabla completa**: Detalle de las 52 comunas

## ⚙️ Configuración avanzada

### Cambiar frecuencia de ejecución

Edita `.github/workflows/monitor.yml`:

```yaml
schedule:
  - cron: '*/10 * * * *'  # Cada 10 minutos (default)
  - cron: '0 * * * *'     # Cada hora
  - cron: '0 */6 * * *'   # Cada 6 horas
```

### Ejecutar localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar monitor de categorías
python monitor.py --workers 5 --output-dir ./output

# Ejecutar monitor de despacho
python delivery_monitor.py \
  --producto 53880 \
  --total 554990 \
  --workers 5 \
  --output-dir ./output

# Abrir dashboards
open ./output/index.html      # macOS
open ./output/delivery.html   # macOS
```

### Opciones de línea de comandos

#### monitor.py (Categorías)
```
--workers N       Número de workers paralelos (default: 3)
--delay-min F     Delay mínimo entre requests (default: 0.35)
--delay-max F     Delay máximo entre requests (default: 0.9)
--output-dir PATH Directorio de salida (default: ./output)
```

#### delivery_monitor.py (Despacho)
```
--producto ID     ID del producto (requerido)
--total MONTO     Total del carrito (requerido)
--tienda ID       ID de tienda (default: 11 = Internet)
--cantidad N      Cantidad de productos (default: 1)
--workers N       Número de workers paralelos (default: 3)
--output-dir PATH Directorio de salida (default: ./output)
```

## 📁 Estructura del proyecto

```
pcfactory-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml      # GitHub Actions workflow
├── monitor.py               # Monitor de categorías
├── delivery_monitor.py      # Monitor de despacho RM
├── requirements.txt         # Dependencias Python
└── README.md               # Este archivo
```

## 📤 Outputs generados

```
output/
├── index.html              # Dashboard de categorías
├── report.json             # Datos JSON de categorías
├── delivery.html           # Dashboard de despacho
└── delivery_report.json    # Datos JSON de despacho
```

## 🔧 Troubleshooting

### El workflow no se ejecuta
- Verifica que el repositorio sea público
- Ve a Settings > Actions y asegúrate de que Actions está habilitado

### GitHub Pages no funciona
- Ve a Settings > Pages
- Asegúrate de que la fuente sea "GitHub Actions"
- El primer deploy puede tardar unos minutos

### Error de permisos
- Ve a Settings > Actions > General
- Habilita "Read and write permissions"

### Delivery muestra 0% cobertura
- Verifica que el producto tenga stock
- Prueba con otro producto que sepas que tiene disponibilidad

## 📝 Notas

- El monitor respeta delays entre requests para no sobrecargar la API
- Los dashboards se auto-refrescan cada 10 minutos en el navegador
- Los datos JSON permiten integraciones con otras herramientas

## 📜 Licencia

Uso personal. Prohibido replicar el uso de los mismos endpoints para fines comerciales.

---

Hecho con ❤️ por Ain Catoni
