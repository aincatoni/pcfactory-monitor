#!/usr/bin/env python3
"""
PCFactory Category Monitor
Verifica el estado de todas las categorías y genera un reporte JSON + HTML
Basado en menu_status_v3.py
"""
import json
import time
import random
import argparse
import concurrent.futures as cf
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (igual que menu_status_v3.py)
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_ENDPOINT = "https://api.pcfactory.cl/api-dex-catalog/v1/catalog/category/PCF"
PRODUCTS_API_BASE = "https://api.pcfactory.cl/pcfactory-services-catalogo/v1/catalogo/productos/query"
BASE_CATEG_URL = "https://www.pcfactory.cl/categoria"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6_1) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# ═══════════════════════════════════════════════════════════════════════════════
# SESIÓN HTTP (igual que menu_status_v3.py)
# ═══════════════════════════════════════════════════════════════════════════════

def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA, 
        "Accept": "application/json, text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    retry = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def polite_pause(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE EXTRACCIÓN (igual que menu_status_v3.py)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_menu(session: requests.Session, endpoint: str):
    r = session.get(endpoint, timeout=30)
    r.raise_for_status()
    return r.json()

def walk_links(nodes: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    stack = list(nodes or [])
    while stack:
        n = stack.pop()
        link = n.get("link") or n.get("Link")
        if link:
            out.append({"id": n.get("id"), "nombre": n.get("nombre") or n.get("Nombre"), "link": str(link)})
        childs = n.get("childCategories") or n.get("childcategories") or []
        if isinstance(childs, list) and childs:
            stack.extend(childs)
    # únicos por link
    seen, unique = set(), []
    for it in out:
        if it["link"] not in seen:
            seen.add(it["link"])
            unique.append(it)
    return unique

def build_full_url(link: str) -> str:
    link = link.strip()
    if link.startswith("http://") or link.startswith("https://"):
        return link
    return BASE_CATEG_URL.rstrip("/") + "/" + link.lstrip("/")

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE CATEGORÍAS (igual que menu_status_v3.py)
# ═══════════════════════════════════════════════════════════════════════════════

def check_products(session: requests.Session, category_id: int, min_delay: float, max_delay: float) -> Dict[str, Any]:
    """Consulta la API de productos para ver cuántos tiene una categoría."""
    polite_pause(min_delay, max_delay)
    try:
        # API correcta: /query?page=0&size=1&categorias=ID
        url = f"{PRODUCTS_API_BASE}?page=0&size=1&categorias={category_id}"
        resp = session.get(url, timeout=20)
        
        if resp.status_code == 429 and "Retry-After" in resp.headers:
            try:
                wait = int(resp.headers["Retry-After"])
                time.sleep(min(wait, 20))
            except Exception:
                pass
        
        if resp.ok:
            data = resp.json()
            content = data.get("content", {})
            pageable = content.get("pageable", {})
            total = pageable.get("totalElements", 0)
            return {
                "total_productos": total,
                "tiene_productos": total > 0,
                "productos_api_status": resp.status_code,
                "productos_error": "",
            }
        else:
            return {
                "total_productos": None,
                "tiene_productos": None,
                "productos_api_status": resp.status_code,
                "productos_error": f"HTTP {resp.status_code}",
            }
    except requests.RequestException as e:
        return {
            "total_productos": None,
            "tiene_productos": None,
            "productos_api_status": None,
            "productos_error": str(e),
        }

def probe(session: requests.Session, url: str, min_delay: float, max_delay: float) -> Dict[str, Any]:
    t0 = time.perf_counter()
    polite_pause(min_delay, max_delay)
    try:
        resp = session.get(url, allow_redirects=True, timeout=25)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        if resp.status_code == 429 and "Retry-After" in resp.headers:
            try:
                wait = int(resp.headers["Retry-After"])
                time.sleep(min(wait, 20))
            except Exception:
                pass
        return {
            "status_code": resp.status_code,
            "ok": resp.ok,
            "elapsed_ms": elapsed_ms,
            "error": "",
        }
    except requests.RequestException as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {"status_code": None, "ok": False, "elapsed_ms": elapsed_ms, "error": str(e)}

def probe_with_products(session: requests.Session, item: Dict[str, Any], url: str, 
                        min_delay: float, max_delay: float) -> Dict[str, Any]:
    """Hace probe de URL y verifica productos."""
    url_result = probe(session, url, min_delay, max_delay)
    
    result = {
        "id": item.get("id"),
        "nombre": item.get("nombre"),
        "link": item.get("link"),
        "url": url,
        **url_result,
    }
    
    # Verificar productos si tenemos ID
    if item.get("id"):
        prod_result = check_products(session, item["id"], min_delay, max_delay)
        result.update(prod_result)
    else:
        result.update({
            "total_productos": None,
            "tiene_productos": None,
            "productos_api_status": None,
            "productos_error": "ID no disponible",
        })
    
    return result

def run_monitor(workers: int = 3, delay_min: float = 0.35, delay_max: float = 0.9) -> Dict:
    """Ejecuta el monitoreo completo y retorna resultados."""
    session = create_session()
    
    print(f"📡 Descargando menú: {DEFAULT_ENDPOINT}")
    data = fetch_menu(session, DEFAULT_ENDPOINT)
    nodes = data if isinstance(data, list) else data.get("data", [])
    items = walk_links(nodes)
    
    print(f"📦 Links encontrados: {len(items)}")
    print(f"✓ Verificación de productos ACTIVADA")
    print(f"  API: {PRODUCTS_API_BASE}?page=0&size=1&categorias=<ID>")
    
    results = []
    total = len(items)
    
    print(f"\n🔍 Verificando categorías con {workers} workers...")
    
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(probe_with_products, session, item, build_full_url(item["link"]), 
                          delay_min, delay_max): item 
            for item in items
        }
        
        for i, future in enumerate(cf.as_completed(future_map), 1):
            try:
                result = future.result()
                results.append(result)
                
                # Progreso (igual que el original)
                status_emoji = "✓" if result["ok"] else "✗"
                prod_info = ""
                if result.get("total_productos") is not None:
                    prod_emoji = "📦" if result["tiene_productos"] else "📭"
                    prod_info = f" {prod_emoji} {result['total_productos']} prods"
                print(f"[{i}/{total}] {status_emoji} {result['nombre'][:40]:<40}{prod_info}")
                
            except Exception as e:
                item = future_map[future]
                print(f"[{i}/{total}] ⚠️ Error en {item['nombre']}: {e}")
    
    # Ordenar igual que el script original
    def sort_key(r):
        ok_order = 0 if r["ok"] else 1
        prod_order = 0
        if r.get("tiene_productos") is False:
            prod_order = 1
        elif r.get("tiene_productos") is None:
            prod_order = 2
        return (ok_order, prod_order, r["status_code"] if r["status_code"] is not None else 9999, r["url"])
    
    results.sort(key=sort_key)
    
    # Calcular estadísticas
    total_cats = len(results)
    urls_ok = sum(1 for r in results if r["ok"])
    urls_error = total_cats - urls_ok
    con_productos = sum(1 for r in results if r.get("tiene_productos") == True)
    sin_productos = sum(1 for r in results if r.get("tiene_productos") == False)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    report = {
        "timestamp": timestamp,
        "summary": {
            "total_categorias": total_cats,
            "urls_ok": urls_ok,
            "urls_error": urls_error,
            "con_productos": con_productos,
            "sin_productos": sin_productos,
            "health_score": round((con_productos / total_cats) * 100, 1) if total_cats > 0 else 0,
        },
        "categorias_vacias": [
            {"id": r["id"], "nombre": r["nombre"], "url": r["url"]}
            for r in results if r.get("tiene_productos") == False
        ],
        "categorias_error": [
            {"id": r["id"], "nombre": r["nombre"], "url": r["url"], "status": r["status_code"], "error": r["error"]}
            for r in results if not r["ok"]
        ],
        "all_categories": results,
    }
    
    return report

# ═══════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE HTML
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html_dashboard(report: Dict) -> str:
    """Genera un dashboard HTML moderno con los resultados."""
    summary = report["summary"]
    timestamp = report["timestamp"]
    vacias = report["categorias_vacias"]
    errores = report["categorias_error"]
    all_cats = report["all_categories"]
    
    # Formatear timestamp para mostrar
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        timestamp_display = dt.strftime("%d/%m/%Y %H:%M:%S UTC")
    except:
        timestamp_display = timestamp
    
    # Determinar estado general
    if summary["urls_error"] > 0:
        status_class = "critical"
        status_text = "⚠️ Hay URLs con error"
        status_color = "#ef4444"
    elif summary["sin_productos"] > 0:
        status_class = "warning"
        status_text = f"⚡ {summary['sin_productos']} categorías vacías"
        status_color = "#f59e0b"
    else:
        status_class = "healthy"
        status_text = "✅ Todo OK"
        status_color = "#10b981"
    
    # Generar filas de categorías vacías
    vacias_rows = ""
    for cat in vacias:
        vacias_rows += f'''
        <tr>
            <td><span class="badge badge-id">{cat["id"]}</span></td>
            <td>{cat["nombre"]}</td>
            <td><a href="{cat["url"]}" target="_blank" class="link">Ver →</a></td>
        </tr>'''
    
    # Generar filas de errores
    errores_rows = ""
    for cat in errores:
        errores_rows += f'''
        <tr class="error-row">
            <td><span class="badge badge-error">{cat["status"] or "ERR"}</span></td>
            <td>{cat["nombre"]}</td>
            <td><a href="{cat["url"]}" target="_blank" class="link">Ver →</a></td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="600">
    <title>PCFactory Monitor - Dashboard</title>
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
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Header */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .logo-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }}
        
        .logo-text h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        
        .logo-text span {{
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        
        .timestamp {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-secondary);
            background: var(--bg-card);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        
        .timestamp::before {{
            content: "🕐 ";
        }}
        
        /* Status Banner */
        .status-banner {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .status-banner.critical {{
            border-color: var(--accent-red);
            background: rgba(239, 68, 68, 0.1);
        }}
        
        .status-banner.warning {{
            border-color: var(--accent-yellow);
            background: rgba(245, 158, 11, 0.1);
        }}
        
        .status-banner.healthy {{
            border-color: var(--accent-green);
            background: rgba(16, 185, 129, 0.1);
        }}
        
        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        .status-banner.critical .status-indicator {{ background: var(--accent-red); }}
        .status-banner.warning .status-indicator {{ background: var(--accent-yellow); }}
        .status-banner.healthy .status-indicator {{ background: var(--accent-green); }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .status-text {{
            font-size: 1.125rem;
            font-weight: 600;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
        }}
        
        .stat-card:hover {{
            background: var(--bg-hover);
            transform: translateY(-2px);
        }}
        
        .stat-label {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .stat-value {{
            font-family: var(--font-mono);
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .stat-value.green {{ color: var(--accent-green); }}
        .stat-value.yellow {{ color: var(--accent-yellow); }}
        .stat-value.red {{ color: var(--accent-red); }}
        .stat-value.blue {{ color: var(--accent-blue); }}
        
        /* Health Score */
        .health-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            text-align: center;
        }}
        
        .health-score {{
            font-family: var(--font-mono);
            font-size: 4rem;
            font-weight: 700;
            background: linear-gradient(135deg, {status_color}, var(--text-primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .health-label {{
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}
        
        /* Sections */
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        
        .section-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .section-header h2 {{
            font-size: 1rem;
            font-weight: 600;
        }}
        
        .section-count {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            background: var(--bg-hover);
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            color: var(--text-secondary);
        }}
        
        /* Table */
        .table-container {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            text-align: left;
            padding: 1rem 1.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            background: var(--bg-secondary);
            font-weight: 600;
        }}
        
        td {{
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.875rem;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover {{
            background: var(--bg-hover);
        }}
        
        .error-row {{
            background: rgba(239, 68, 68, 0.05);
        }}
        
        /* Badges */
        .badge {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        
        .badge-id {{
            background: var(--bg-hover);
            color: var(--text-secondary);
        }}
        
        .badge-error {{
            background: rgba(239, 68, 68, 0.2);
            color: var(--accent-red);
        }}
        
        .badge-ok {{
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }}
        
        /* Links */
        .link {{
            color: var(--accent-blue);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }}
        
        .link:hover {{
            color: var(--text-primary);
        }}
        
        /* Empty State */
        .empty-state {{
            padding: 3rem;
            text-align: center;
            color: var(--text-muted);
        }}
        
        .empty-state-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header {{
                flex-direction: column;
                gap: 1rem;
                text-align: center;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .health-score {{
                font-size: 3rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">📊</div>
                <div class="logo-text">
                    <h1>PCFactory Monitor</h1>
                    <span>Monitoreo de Categorías</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <!-- Status Banner -->
        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>
        
        <!-- Health Score -->
        <div class="health-card">
            <div class="health-score">{summary["health_score"]}%</div>
            <div class="health-label">Health Score (categorías con productos)</div>
        </div>
        
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Categorías</div>
                <div class="stat-value blue">{summary["total_categorias"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLs OK</div>
                <div class="stat-value green">{summary["urls_ok"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLs Error</div>
                <div class="stat-value {"red" if summary["urls_error"] > 0 else "green"}">{summary["urls_error"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Con Productos</div>
                <div class="stat-value green">{summary["con_productos"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sin Productos</div>
                <div class="stat-value {"yellow" if summary["sin_productos"] > 0 else "green"}">{summary["sin_productos"]}</div>
            </div>
        </div>
        
        <!-- Errores Section -->
        {"" if not errores else f'''
        <div class="section">
            <div class="section-header">
                <span>🚨</span>
                <h2>URLs con Error</h2>
                <span class="section-count">{len(errores)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Categoría</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {errores_rows}
                    </tbody>
                </table>
            </div>
        </div>
        '''}
        
        <!-- Categorías Vacías Section -->
        {"" if not vacias else f'''
        <div class="section">
            <div class="section-header">
                <span>📭</span>
                <h2>Categorías Sin Productos</h2>
                <span class="section-count">{len(vacias)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Categoría</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
                        {vacias_rows}
                    </tbody>
                </table>
            </div>
        </div>
        '''}
        
        <!-- All OK Message -->
        {'''
        <div class="section">
            <div class="empty-state">
                <div class="empty-state-icon">🎉</div>
                <p>¡Todas las categorías están funcionando correctamente!</p>
            </div>
        </div>
        ''' if not errores and not vacias else ''}
        
        <!-- Footer -->
        <footer class="footer">
            <p>Actualización automática cada 10 minutos • Powered by GitHub Actions</p>
        </footer>
    </div>
    
    <script>
        // Auto-refresh countdown (opcional)
        const refreshSeconds = 600;
        let countdown = refreshSeconds;
        
        setInterval(() => {{
            countdown--;
            if (countdown <= 0) {{
                location.reload();
            }}
        }}, 1000);
    </script>
</body>
</html>'''
    
    return html

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="PCFactory Category Monitor")
    parser.add_argument("--workers", type=int, default=3, help="Máximo de peticiones concurrentes (recomendado 2-4)")
    parser.add_argument("--delay-min", type=float, default=0.35, help="Pausa mínima entre requests (segundos)")
    parser.add_argument("--delay-max", type=float, default=0.9, help="Pausa máxima entre requests (segundos)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directorio de salida")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🖥️  PCFactory Category Monitor")
    print("=" * 60)
    
    # Ejecutar monitoreo
    report = run_monitor(
        workers=args.workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max
    )
    
    # Guardar JSON
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 JSON guardado: {json_path}")
    
    # Guardar HTML
    html_content = generate_html_dashboard(report)
    html_path = output_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"🌐 HTML guardado: {html_path}")
    
    # Resumen final (igual que el original)
    summary = report["summary"]
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total categorías: {summary['total_categorias']}")
    print(f"URLs OK (200): {summary['urls_ok']}")
    print(f"URLs con error: {summary['urls_error']}")
    print(f"Categorías CON productos: {summary['con_productos']}")
    print(f"Categorías SIN productos: {summary['sin_productos']} ⚠️")
    
    if report["categorias_vacias"]:
        print(f"\nCategorías vacías (sin productos):")
        for cat in report["categorias_vacias"]:
            print(f"  - [{cat['id']}] {cat['nombre']}")
    
    print(f"\n✅ Archivo guardado: {args.output_dir}")

if __name__ == "__main__":
    main()
