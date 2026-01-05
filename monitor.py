#!/usr/bin/env python3
"""
PCFactory Category Monitor
Verifica el estado de todas las categorías y genera un reporte JSON + HTML
"""
import json
import time
import random
import argparse
import concurrent.futures as cf
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

MENU_ENDPOINT = "https://api.pcfactory.cl/api-dex-catalog/v1/catalog/category/PCF"
PRODUCTS_API = "https://api.pcfactory.cl/pcfactory-services-catalogo/v1/catalogo/productos/query"
BASE_CATEG_URL = "https://www.pcfactory.cl/categoria"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE FECHA/HORA CHILE
# ═══════════════════════════════════════════════════════════════════════════════

def utc_to_chile(dt_utc):
    """Convierte datetime UTC a hora Chile (UTC-3 verano, UTC-4 invierno)."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    # Chile usa UTC-3 en verano (sept-abril) y UTC-4 en invierno (abril-sept)
    # Simplificación: usar UTC-3 (horario de verano actual)
    chile_offset = timedelta(hours=-3)
    chile_tz = timezone(chile_offset)
    
    return dt_utc.astimezone(chile_tz)

def get_chile_timestamp():
    """Retorna timestamp actual en hora Chile."""
    now_utc = datetime.now(timezone.utc)
    now_chile = utc_to_chile(now_utc)
    return now_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'

# ═══════════════════════════════════════════════════════════════════════════════
# SESIÓN HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/html, */*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    })
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE EXTRACCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_menu(session: requests.Session) -> List[Dict]:
    """Obtiene el menú de categorías desde la API."""
    resp = session.get(MENU_ENDPOINT, timeout=30)
    resp.raise_for_status()
    return resp.json()

def walk_categories(nodes: List[Dict]) -> List[Dict[str, Any]]:
    """Extrae todas las categorías con su ID, nombre y link."""
    result = []
    def _walk(items: List[Dict]):
        for item in items:
            cat_id = item.get("id", "")
            name = item.get("name", "")
            link = item.get("link", "")
            if cat_id and link:
                result.append({
                    "id": cat_id,
                    "nombre": name,
                    "link": link,
                    "url": f"{BASE_CATEG_URL}/{link}"
                })
            children = item.get("children", [])
            if children:
                _walk(children)
    _walk(nodes)
    return result

def check_category(session: requests.Session, category: Dict, delay: float) -> Dict:
    """Verifica una categoría: URL accesible y productos disponibles."""
    time.sleep(delay)
    
    cat_id = category["id"]
    url = category["url"]
    
    result = {
        "id": cat_id,
        "nombre": category["nombre"],
        "url": url,
        "status": None,
        "tiene_productos": False,
        "cantidad_productos": 0,
        "error": None
    }
    
    # Verificar URL
    try:
        resp = session.get(url, timeout=15, allow_redirects=True)
        result["status"] = resp.status_code
    except Exception as e:
        result["error"] = str(e)
        return result
    
    # Verificar productos via API
    try:
        payload = {
            "idCategoria": cat_id,
            "pagina": 1,
            "orden": "score",
            "filtros": "",
            "precioMin": None,
            "precioMax": None
        }
        resp = session.post(PRODUCTS_API, json=payload, timeout=15)
        if resp.ok:
            data = resp.json()
            total = data.get("totalResultados", 0)
            result["cantidad_productos"] = total
            result["tiene_productos"] = total > 0
    except Exception as e:
        result["error"] = f"Error API productos: {e}"
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# MONITOREO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_monitor(workers: int = 5, delay_min: float = 0.2, delay_max: float = 0.5) -> Dict:
    """Ejecuta el monitoreo completo."""
    session = create_session()
    
    print("[*] Obteniendo menu de categorias...")
    menu = fetch_menu(session)
    categories = walk_categories(menu)
    print(f"[+] {len(categories)} categorias encontradas")
    
    results = []
    print(f"[*] Verificando categorias ({workers} workers)...")
    
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for cat in categories:
            delay = random.uniform(delay_min, delay_max)
            fut = executor.submit(check_category, session, cat, delay)
            futures[fut] = cat
        
        done = 0
        for fut in cf.as_completed(futures):
            done += 1
            if done % 50 == 0 or done == len(categories):
                print(f"    {done}/{len(categories)} verificadas...")
            try:
                results.append(fut.result())
            except Exception as e:
                cat = futures[fut]
                results.append({
                    "id": cat["id"],
                    "nombre": cat["nombre"],
                    "url": cat["url"],
                    "status": None,
                    "tiene_productos": False,
                    "cantidad_productos": 0,
                    "error": str(e)
                })
    
    # Calcular resumen
    urls_ok = len([r for r in results if r["status"] == 200])
    urls_error = len([r for r in results if r["status"] != 200])
    con_productos = len([r for r in results if r["tiene_productos"]])
    sin_productos = len([r for r in results if not r["tiene_productos"] and r["status"] == 200])
    
    categorias_vacias = [
        {"id": r["id"], "nombre": r["nombre"], "url": r["url"]}
        for r in results if not r["tiene_productos"] and r["status"] == 200
    ]
    
    categorias_error = [
        {"id": r["id"], "nombre": r["nombre"], "url": r["url"], "status": r["status"], "error": r.get("error")}
        for r in results if r["status"] != 200
    ]
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_categorias": len(categories),
            "urls_ok": urls_ok,
            "urls_error": urls_error,
            "con_productos": con_productos,
            "sin_productos": sin_productos
        },
        "categorias_vacias": categorias_vacias,
        "categorias_error": categorias_error,
        "all_results": results
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html_dashboard(report: Dict) -> str:
    """Genera el dashboard HTML."""
    summary = report["summary"]
    vacias = report.get("categorias_vacias", [])
    errores = report.get("categorias_error", [])
    timestamp = report.get("timestamp", "")
    
    # Convertir timestamp a hora Chile
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        dt_chile = utc_to_chile(dt)
        timestamp_display = dt_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'
    except:
        timestamp_display = timestamp
    
    # Calcular health score
    total = summary["total_categorias"]
    if total > 0:
        health_score = (summary["con_productos"] / total) * 100
    else:
        health_score = 0
    
    if summary["urls_error"] > 0:
        status_class = "critical"
        status_text = "Hay URLs con error"
        status_color = "#ef4444"
    elif summary["sin_productos"] > 0:
        status_class = "warning"
        status_text = f"{summary['sin_productos']} categorias vacias"
        status_color = "#f59e0b"
    else:
        status_class = "healthy"
        status_text = "Todo OK"
        status_color = "#10b981"
    
    vacias_rows = ""
    for cat in vacias:
        vacias_rows += f'''
        <tr>
            <td><span class="badge badge-id">{cat["id"]}</span></td>
            <td>{cat["nombre"]}</td>
            <td><a href="{cat["url"]}" target="_blank" class="link">Ver</a></td>
        </tr>'''
    
    errores_rows = ""
    for cat in errores:
        errores_rows += f'''
        <tr class="error-row">
            <td><span class="badge badge-error">{cat["status"] or "ERR"}</span></td>
            <td>{cat["nombre"]}</td>
            <td><a href="{cat["url"]}" target="_blank" class="link">Ver</a></td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="600">
    <title>PCFactory Monitor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --bg-hover: #22222e;
            --text-primary: #f4f4f5;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --accent-green: #10b981;
            --accent-yellow: #f59e0b;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --border: #27272a;
            --font-mono: 'JetBrains Mono', monospace;
            --font-sans: 'Space Grotesk', sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding-bottom: 2rem;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .logo {{ display: flex; align-items: center; gap: 1rem; }}
        .logo-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.25rem;
        }}
        .logo-text h1 {{ font-size: 1.5rem; font-weight: 600; }}
        .logo-text span {{ font-size: 0.875rem; color: var(--text-secondary); }}
        .timestamp {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-muted);
            background: var(--bg-card);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .nav-links {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        .nav-link {{
            padding: 0.625rem 1.25rem;
            border-radius: 8px;
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-secondary);
        }}
        .nav-link:hover {{ background: var(--bg-hover); color: var(--text-primary); }}
        .nav-link.active {{
            background: var(--accent-green);
            color: white;
            border-color: var(--accent-green);
        }}
        .status-banner {{
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 500;
        }}
        .status-banner.healthy {{ background: rgba(16, 185, 129, 0.15); border: 1px solid var(--accent-green); color: var(--accent-green); }}
        .status-banner.warning {{ background: rgba(245, 158, 11, 0.15); border: 1px solid var(--accent-yellow); color: var(--accent-yellow); }}
        .status-banner.critical {{ background: rgba(239, 68, 68, 0.15); border: 1px solid var(--accent-red); color: var(--accent-red); }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .hero-score {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 3rem;
            text-align: center;
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }}
        .score-value {{
            font-family: var(--font-mono);
            font-size: 5rem;
            font-weight: 700;
            color: {status_color};
            line-height: 1;
        }}
        .score-label {{
            color: var(--text-secondary);
            margin-top: 0.5rem;
            font-size: 1rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }}
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        .stat-value {{
            font-family: var(--font-mono);
            font-size: 2rem;
            font-weight: 600;
            color: var(--accent-green);
        }}
        .stat-value.warning {{ color: var(--accent-yellow); }}
        .stat-value.error {{ color: var(--accent-red); }}
        .section {{ margin-bottom: 2rem; }}
        .section-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .data-table th, .data-table td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        .data-table th {{
            background: var(--bg-secondary);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table tr:hover td {{ background: var(--bg-hover); }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: var(--font-mono);
        }}
        .badge-id {{ background: var(--bg-secondary); color: var(--text-secondary); }}
        .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
        .link {{
            color: var(--accent-blue);
            text-decoration: none;
        }}
        .link:hover {{ text-decoration: underline; }}
        .error-row td {{ background: rgba(239, 68, 68, 0.05); }}
        .all-ok {{
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
        }}
        .all-ok-icon {{ font-size: 3rem; margin-bottom: 1rem; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .score-value {{ font-size: 3rem; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <div class="logo-icon">PC</div>
                <div class="logo-text">
                    <h1>pc Factory Monitor</h1>
                    <span>Monitoreo de Categorias</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <nav class="nav-links">
            <a href="index.html" class="nav-link active">📦 Categorias</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
        </nav>
        
        <div class="status-banner {status_class}">
            <span class="status-dot"></span>
            {status_text}
        </div>
        
        <div class="hero-score">
            <div class="score-value">{health_score:.1f}%</div>
            <div class="score-label">Health Score (categorias con productos)</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">TOTAL CATEGORIAS</div>
                <div class="stat-value">{summary["total_categorias"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLS OK</div>
                <div class="stat-value">{summary["urls_ok"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLS ERROR</div>
                <div class="stat-value {"error" if summary["urls_error"] > 0 else ""}">{summary["urls_error"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">CON PRODUCTOS</div>
                <div class="stat-value">{summary["con_productos"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">SIN PRODUCTOS</div>
                <div class="stat-value {"warning" if summary["sin_productos"] > 0 else ""}">{summary["sin_productos"]}</div>
            </div>
        </div>
        '''
    
    # Sección de errores
    if errores:
        html += f'''
        <div class="section">
            <h2 class="section-title">❌ URLs con Error ({len(errores)})</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Categoria</th>
                        <th>Enlace</th>
                    </tr>
                </thead>
                <tbody>
                    {errores_rows}
                </tbody>
            </table>
        </div>
        '''
    
    # Sección de vacías
    if vacias:
        html += f'''
        <div class="section">
            <h2 class="section-title">⚠️ Categorias Vacias ({len(vacias)})</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Categoria</th>
                        <th>Enlace</th>
                    </tr>
                </thead>
                <tbody>
                    {vacias_rows}
                </tbody>
            </table>
        </div>
        '''
    
    # Si todo OK
    if not errores and not vacias:
        html += '''
        <div class="all-ok">
            <div class="all-ok-icon">🎉</div>
            <p>Todas las categorias tienen productos y URLs funcionando correctamente</p>
        </div>
        '''
    
    html += '''
        <footer class="footer">
            <p>Actualizacion automatica cada 10 minutos - Powered by GitHub Actions</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="PCFactory Category Monitor")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--delay-min", type=float, default=0.35)
    parser.add_argument("--delay-max", type=float, default=0.9)
    parser.add_argument("--output-dir", type=str, default="./output")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Category Monitor")
    print("=" * 60)
    
    report = run_monitor(
        workers=args.workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max
    )
    
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n[+] JSON guardado: " + str(json_path))
    
    html_content = generate_html_dashboard(report)
    html_path = output_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[+] HTML guardado: " + str(html_path))
    
    summary = report["summary"]
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print("Total categorias: " + str(summary['total_categorias']))
    print("URLs OK (200): " + str(summary['urls_ok']))
    print("URLs con error: " + str(summary['urls_error']))
    print("Categorias CON productos: " + str(summary['con_productos']))
    print("Categorias SIN productos: " + str(summary['sin_productos']))
    
    if report["categorias_vacias"]:
        print("\nCategorias vacias (sin productos):")
        for cat in report["categorias_vacias"]:
            print("  - [" + str(cat['id']) + "] " + str(cat['nombre']))
    
    print("\n[OK] Monitoreo completado!")

if __name__ == "__main__":
    main()
