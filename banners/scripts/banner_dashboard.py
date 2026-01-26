#!/usr/bin/env python3
"""
Generador de Dashboard para Banner Price Monitor
Procesa los resultados del test de Playwright y genera un dashboard HTML
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

def utc_to_chile(dt):
    """Convierte timestamp UTC a hora de Chile"""
    chile_tz = timezone(timedelta(hours=-3))
    return dt.astimezone(chile_tz)

def format_chile_timestamp(iso_timestamp):
    """Formatea timestamp ISO a formato legible en hora de Chile"""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        dt_chile = utc_to_chile(dt)
        return dt_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'
    except:
        return iso_timestamp

def format_price(price):
    """Formatea precio al estilo chileno"""
    if price is None:
        return "N/A"
    return f"${int(price):,}".replace(",", ".")

def generate_html(results_data):
    """Genera el HTML del dashboard"""

    timestamp = results_data.get('timestamp', '')
    timestamp_display = format_chile_timestamp(timestamp)
    banners = results_data.get('banners', [])

    # Estadísticas
    total = len(banners)
    with_price = len([b for b in banners if b.get('bannerPrice')])
    matched = len([b for b in banners if b.get('priceMatch') == True])
    mismatched = len([b for b in banners if b.get('priceMatch') == False])
    no_price = len([b for b in banners if b.get('status') == 'no_price'])
    errors = len([b for b in banners if b.get('status') == 'error'])

    # Generar filas de la tabla
    banner_rows = ""
    for banner in banners:
        index = banner.get('index', 0)
        status = banner.get('status', 'unknown')
        banner_price = banner.get('bannerPrice')
        product_price = banner.get('productPrice')
        product_url = banner.get('productUrl', '')
        screenshot = banner.get('screenshot', '')
        error = banner.get('error', '')
        difference = banner.get('difference', 0)
        percent_diff = banner.get('percentDiff', 0)

        # Badge de estado
        if status == 'match':
            status_badge = '<span class="badge badge-ok">✓ Coincide</span>'
            status_class = 'match-row'
        elif status == 'mismatch':
            status_badge = f'<span class="badge badge-error">✗ No Coincide ({percent_diff:.1f}%)</span>'
            status_class = 'mismatch-row'
        elif status == 'no_price':
            status_badge = '<span class="badge badge-muted">Sin Precio</span>'
            status_class = ''
        elif status == 'error':
            status_badge = '<span class="badge badge-warning">Error</span>'
            status_class = 'error-row'
        else:
            status_badge = '<span class="badge badge-muted">N/A</span>'
            status_class = ''

        # Precios
        banner_price_display = format_price(banner_price)
        product_price_display = format_price(product_price)

        # Link del producto
        product_link = ''
        if product_url:
            product_link = f'<a href="{product_url}" target="_blank" class="link">Ver</a>'

        # Screenshot button
        screenshot_btn = ''
        if screenshot:
            screenshot_btn = f'''
                <button class="screenshot-btn" onclick="openScreenshot('screenshots/{screenshot}', 'Banner {index}')">
                    📸 Ver
                </button>
            '''

        # Error message
        error_msg = ''
        if error:
            error_msg = f'<div class="error-text">{error[:100]}</div>'

        banner_rows += f'''
            <tr class="{status_class}">
                <td><span class="badge badge-id">{index}</span></td>
                <td>{status_badge}</td>
                <td>{banner_price_display}</td>
                <td>{product_price_display}</td>
                <td>{product_link}</td>
                <td>{screenshot_btn}</td>
            </tr>
        '''

        if error_msg:
            banner_rows += f'''
                <tr class="{status_class}">
                    <td colspan="6">{error_msg}</td>
                </tr>
            '''

    # Health score
    if with_price > 0:
        health_score = round((matched / with_price) * 100, 1)
    else:
        health_score = 0

    # Status class
    if health_score == 100:
        status_class = "status-ok"
        status_text = "Todos los precios coinciden"
        health_message = "¡Perfecto! Todos los banners con precio tienen información correcta"
    elif health_score >= 80:
        status_class = "status-warning"
        status_text = f"{mismatched} banner(es) con precio incorrecto"
        health_message = "La mayoría de los banners tienen precios correctos"
    else:
        status_class = "status-error"
        status_text = f"{mismatched} banner(es) con precio incorrecto"
        health_message = "Múltiples banners requieren revisión"

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCFactory Banner Monitor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #16161f;
            --bg-hover: #1e1e2a;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --text-muted: #606070;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
            --accent-blue: #3b82f6;
            --font-sans: 'Ubuntu', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 1rem; }}
        .logo {{ display: flex; align-items: center; gap: 1rem; }}
        .logo-icon {{ width: 48px; height: 48px; background: linear-gradient(135deg, var(--accent-blue), var(--accent-green)); border-radius: 12px; display: flex; align-items: center; justify-content: center; }}
        .logo-icon img {{ width: 32px; height: 32px; }}
        .logo-text h1 {{ font-size: 1.5rem; font-weight: 700; }}
        .logo-text span {{ font-size: 0.875rem; color: var(--text-muted); }}
        .timestamp {{ font-family: var(--font-mono); font-size: 0.875rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border); }}

        .nav-links {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
        .nav-link {{ font-family: var(--font-mono); font-size: 0.875rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.625rem 1rem; border-radius: 8px; text-decoration: none; border: 1px solid var(--border); transition: all 0.2s; }}
        .nav-link:hover {{ background: var(--bg-hover); color: var(--text-primary); }}
        .nav-link.active {{ background: var(--accent-green); color: #000000; border-color: var(--accent-green); font-weight: 500; }}

        .status-banner {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 1rem; }}
        .status-banner.status-ok {{ border-color: var(--accent-green); }}
        .status-banner.status-warning {{ border-color: var(--accent-yellow); }}
        .status-banner.status-error {{ border-color: var(--accent-red); }}
        .status-indicator {{ width: 12px; height: 12px; border-radius: 50%; background: var(--accent-green); }}
        .status-banner.status-warning .status-indicator {{ background: var(--accent-yellow); }}
        .status-banner.status-error .status-indicator {{ background: var(--accent-red); }}
        .status-text {{ font-size: 1rem; font-weight: 500; }}

        .health-card {{ background: linear-gradient(135deg, var(--bg-card), var(--bg-secondary)); border: 1px solid var(--border); border-radius: 16px; padding: 2rem; text-align: center; margin-bottom: 2rem; }}
        .health-score {{ font-size: 4rem; font-weight: 700; background: linear-gradient(135deg, var(--accent-green), var(--accent-blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }}
        .health-label {{ font-size: 0.875rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
        .health-message {{ font-size: 1rem; color: var(--text-secondary); }}

        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; text-align: center; }}
        .stat-label {{ font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; }}
        .stat-value.green {{ color: var(--accent-green); }}
        .stat-value.red {{ color: var(--accent-red); }}
        .stat-value.yellow {{ color: var(--accent-yellow); }}
        .stat-value.blue {{ color: var(--accent-blue); }}

        .section {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; }}
        .section-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }}
        .section-header span {{ font-size: 1.5rem; }}
        .section-header h2 {{ font-size: 1.25rem; font-weight: 600; }}

        .table-container {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th {{ background: var(--bg-secondary); color: var(--text-secondary); font-weight: 600; text-align: left; padding: 1rem; border-bottom: 2px solid var(--border); }}
        td {{ padding: 1rem; border-bottom: 1px solid var(--border); }}
        tr:hover {{ background: var(--bg-hover); }}
        tr.match-row {{ background: rgba(16, 185, 129, 0.05); }}
        tr.mismatch-row {{ background: rgba(239, 68, 68, 0.05); }}
        tr.error-row {{ background: rgba(245, 158, 11, 0.05); }}

        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; font-family: var(--font-mono); }}
        .badge-id {{ background: var(--bg-secondary); color: var(--text-secondary); }}
        .badge-ok {{ background: var(--accent-green); color: white; }}
        .badge-error {{ background: var(--accent-red); color: white; }}
        .badge-warning {{ background: var(--accent-yellow); color: white; }}
        .badge-muted {{ background: var(--bg-secondary); color: var(--text-muted); }}

        .link {{ color: var(--accent-blue); text-decoration: none; }}
        .link:hover {{ text-decoration: underline; }}

        .screenshot-btn {{ background: var(--accent-blue); color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.75rem; font-family: var(--font-mono); }}
        .screenshot-btn:hover {{ background: #2563eb; }}

        .error-text {{ color: var(--accent-yellow); font-size: 0.75rem; padding: 0.5rem; }}

        /* Modal para screenshots */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.9); z-index: 1000; justify-content: center; align-items: center; }}
        .modal.active {{ display: flex; }}
        .modal-content {{ max-width: 90vw; max-height: 90vh; position: relative; }}
        .modal-close {{ position: absolute; top: -40px; right: 0; background: none; border: none; color: white; font-size: 2rem; cursor: pointer; }}
        .modal-img {{ max-width: 100%; max-height: 90vh; border-radius: 8px; }}

        .footer {{ text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }}

        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <div class="logo-icon"><img src="https://assets-v3.pcfactory.cl/uploads/e964d6b9-e816-439f-8b97-ad2149772b7b/original/pcfactory-isotipo.svg"></div>
                <div class="logo-text"><h1>pc Factory Monitor</h1><span>Monitor de Banners</span></div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>

        <div class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
            <a href="banners.html" class="nav-link active">🎨 Banners</a>
        </div>

        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>

        <div class="health-card">
            <div class="health-score">{health_score}%</div>
            <div class="health-label">Precisión de Precios</div>
            <div class="health-message">{health_message}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Total Banners</div><div class="stat-value blue">{total}</div></div>
            <div class="stat-card"><div class="stat-label">Con Precio</div><div class="stat-value blue">{with_price}</div></div>
            <div class="stat-card"><div class="stat-label">✓ Coinciden</div><div class="stat-value green">{matched}</div></div>
            <div class="stat-card"><div class="stat-label">✗ No Coinciden</div><div class="stat-value red">{mismatched}</div></div>
            <div class="stat-card"><div class="stat-label">Sin Precio</div><div class="stat-value yellow">{no_price}</div></div>
            <div class="stat-card"><div class="stat-label">Errores</div><div class="stat-value red">{errors}</div></div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>🎨</span>
                <h2>Resultados de Análisis de Banners</h2>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Estado</th>
                            <th>Precio Banner</th>
                            <th>Precio Producto</th>
                            <th>Link</th>
                            <th>Screenshot</th>
                        </tr>
                    </thead>
                    <tbody>
                        {banner_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="footer">
            <p>Actualización automática 3 veces al día (9am, 2pm, 8pm Chile)</p>
            <p>Hecho con ❤️ por Ain Cortés Catoni</p>
        </footer>
    </div>

    <!-- Modal para screenshots -->
    <div id="screenshotModal" class="modal" onclick="closeModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <img id="modalImg" class="modal-img" src="" alt="">
        </div>
    </div>

    <script>
        function openScreenshot(imagePath, title) {{
            const modal = document.getElementById('screenshotModal');
            const img = document.getElementById('modalImg');
            img.src = imagePath;
            img.alt = title;
            modal.classList.add('active');
        }}

        function closeModal() {{
            const modal = document.getElementById('screenshotModal');
            modal.classList.remove('active');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>'''

    return html


def main():
    parser = argparse.ArgumentParser(description='PCFactory Banner Dashboard Generator')
    parser.add_argument('--results', type=str, default='./test-results/banner-price-results.json',
                       help='Ruta al archivo de resultados JSON')
    parser.add_argument('--output-dir', type=str, default='./output',
                       help='Directorio de salida')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PCFactory Banner Dashboard Generator")
    print("=" * 60)

    # Cargar resultados
    try:
        with open(args.results, 'r', encoding='utf-8') as f:
            results = json.load(f)
        print(f"✅ Resultados cargados: {args.results}")
    except FileNotFoundError:
        print(f"⚠️ No se encontró archivo de resultados: {args.results}")
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "banners": []
        }

    # Generar HTML
    html = generate_html(results)

    # Guardar dashboard
    output_file = output_dir / 'banners.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_file}")

    # Resumen
    total = len(results.get('banners', []))
    matched = len([b for b in results.get('banners', []) if b.get('priceMatch') == True])
    mismatched = len([b for b in results.get('banners', []) if b.get('priceMatch') == False])

    print(f"\n📊 RESUMEN:")
    print(f"   Total banners: {total}")
    print(f"   ✅ Coinciden: {matched}")
    print(f"   ❌ No coinciden: {mismatched}")
    print("=" * 60)


if __name__ == '__main__':
    main()
