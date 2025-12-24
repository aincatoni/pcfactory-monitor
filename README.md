# 🖥️ PCFactory Category Monitor

Monitoreo automático de categorías de PCFactory que se ejecuta cada 10 minutos y genera un dashboard público.

![Dashboard Preview](https://img.shields.io/badge/status-live-brightgreen)

## 🚀 Cómo configurar

### 1. Crear repositorio en GitHub

1. Ve a [github.com/new](https://github.com/new)
2. Nombre: `pcfactory-monitor` (o el que prefieras)
3. Selecciona **Public** (necesario para GitHub Pages gratis)
4. Click en "Create repository"

### 2. Subir los archivos

```bash
# Clona el repo vacío
git clone https://github.com/TU_USUARIO/pcfactory-monitor.git
cd pcfactory-monitor

# Copia los archivos del monitor aquí
# (monitor.py, requirements.txt, .github/workflows/monitor.yml)

# Sube los cambios
git add .
git commit -m "Initial commit - PCFactory monitor"
git push origin main
```

### 3. Habilitar GitHub Pages

1. Ve a tu repositorio en GitHub
2. Click en **Settings** (⚙️)
3. En el menú lateral, click en **Pages**
4. En "Build and deployment", selecciona:
   - Source: **GitHub Actions**
5. ¡Listo! No necesitas configurar nada más

### 4. Verificar que funciona

1. Ve a la pestaña **Actions** de tu repositorio
2. Deberías ver el workflow "PCFactory Category Monitor"
3. Puedes ejecutarlo manualmente haciendo click en **Run workflow**
4. Una vez que termine, tu dashboard estará en:
   ```
   https://TU_USUARIO.github.io/pcfactory-monitor/
   ```

## 📊 Qué incluye el dashboard

- **Health Score**: Porcentaje de categorías con productos
- **Total categorías**: Número total de categorías
- **URLs OK/Error**: Estado de las URLs
- **Categorías vacías**: Lista de categorías sin productos
- **Auto-refresh**: Se actualiza automáticamente cada 10 minutos

## ⚙️ Configuración avanzada

### Cambiar frecuencia de ejecución

Edita `.github/workflows/monitor.yml` y modifica el cron:

```yaml
schedule:
  - cron: '*/10 * * * *'  # Cada 10 minutos
  - cron: '0 * * * *'     # Cada hora
  - cron: '0 */6 * * *'   # Cada 6 horas
```

### Ejecutar localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar monitor
python monitor.py --workers 5 --output-dir ./output

# Abrir dashboard
open ./output/index.html  # macOS
xdg-open ./output/index.html  # Linux
```

### Notificaciones (opcional)

Puedes agregar notificaciones por Slack, Discord o email. Agrega estos pasos al workflow:

```yaml
- name: 🔔 Notify on issues
  if: ${{ /* condición */ }}
  run: |
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"⚠️ PCFactory: Hay categorías con problemas!"}' \
      ${{ secrets.SLACK_WEBHOOK }}
```

## 📁 Estructura del proyecto

```
pcfactory-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml    # GitHub Actions workflow
├── monitor.py             # Script principal
├── requirements.txt       # Dependencias Python
└── README.md             # Este archivo
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
- Verifica los permisos en el workflow (`permissions:`)
- Puede que necesites ir a Settings > Actions > General y habilitar "Read and write permissions"

## 📝 Licencia
Usar el código pero prohibído replicar el uso de los mismos endpoints
