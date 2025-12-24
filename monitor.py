#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Category Monitor
Verifica el estado de todas las categorias y genera un reporte JSON + HTML
"""
import json
import time
import random
import argparse
import concurrent.futures as cf
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================================================================
# CONFIGURACION
# ==============================================================================

DEFAULT_ENDPOINT = "https://api.pcfactory.cl/api-dex-catalog/v1/catalog/category/PCF"
PRODUCTS_API_BASE = "https://api.pcfactory.cl/pcfactory-services-catalogo/v1/catalogo/productos/query"
BASE_CATEG_URL = "https://www.pcfactory.cl/categoria"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6_1) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# ==============================================================================
# SESION HTTP
# ==============================================================================

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

# ==============================================================================
# FUNCIONES DE EXTRACCION
# ==============================================================================

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

# ==============================================================================
# VERIFICACION DE CATEGORIAS
# ==============================================================================

def check_products(session: requests.Session, category_id: int, min_delay: float, max_delay: float) -> Dict[str, Any]:
    polite_pause(min_delay, max_delay)
    try:
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
    url_result = probe(session, url, min_delay, max_delay)
    
    result = {
        "id": item.get("id"),
        "nombre": item.get("nombre"),
        "link": item.get("link"),
        "url": url,
        **url_result,
    }
    
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
    session = create_session()
    
    print("[*] Descargando menu: " + DEFAULT_ENDPOINT)
    data = fetch_menu(session, DEFAULT_ENDPOINT)
    nodes = data if isinstance(data, list) else data.get("data", [])
    items = walk_links(nodes)
    
    print("[*] Links encontrados: " + str(len(items)))
    print("[+] Verificacion de productos ACTIVADA")
    
    results = []
    total = len(items)
    
    print("\n[*] Verificando categorias con " + str(workers) + " workers...")
    
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
                
                status_mark = "[OK]" if result["ok"] else "[ERR]"
                prod_info = ""
                if result.get("total_productos") is not None:
                    prod_mark = "(+)" if result["tiene_productos"] else "(!)"
                    prod_info = " " + prod_mark + " " + str(result['total_productos']) + " prods"
                nombre_short = result['nombre'][:40] if result['nombre'] else "N/A"
                print("[" + str(i) + "/" + str(total) + "] " + status_mark + " " + nombre_short.ljust(40) + prod_info)
                
            except Exception as e:
                item = future_map[future]
                print("[" + str(i) + "/" + str(total) + "] [WARN] Error en " + str(item['nombre']) + ": " + str(e))
    
    def sort_key(r):
        ok_order = 0 if r["ok"] else 1
        prod_order = 0
        if r.get("tiene_productos") is False:
            prod_order = 1
        elif r.get("tiene_productos") is None:
            prod_order = 2
        return (ok_order, prod_order, r["status_code"] if r["status_code"] is not None else 9999, r["url"])
    
    results.sort(key=sort_key)
    
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

# ==============================================================================
# GENERACION DE HTML
# ==============================================================================

def generate_html_dashboard(report: Dict) -> str:
    summary = report["summary"]
    timestamp = report["timestamp"]
    vacias = report["categorias_vacias"]
    errores = report["categorias_error"]
    
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        timestamp_display = dt.strftime("%d/%m/%Y %H:%M:%S UTC")
    except:
        timestamp_display = timestamp
    
    if summary["urls_error"] > 0:
        status_class = "critical"
        status_text = "Hay URLs con error"
        status_color = "#ef4444"
    elif summary["sin_productos"] > 0:
        status_class = "warning"
        status_text = str(summary['sin_productos']) + " categorias vacias"
        status_color = "#f59e0b"
    else:
        status_class = "healthy"
        status_text = "Todo OK"
        status_color = "#10b981"
    
    # Build rows for empty categories
    vacias_rows = ""
    for cat in vacias:
        cat_id = cat["id"] if cat["id"] else "N/A"
        cat_nombre = cat["nombre"] if cat["nombre"] else "N/A"
        cat_url = cat["url"] if cat["url"] else "#"
        vacias_rows += '<tr>'
        vacias_rows += '<td><span class="badge badge-id">' + str(cat_id) + '</span></td>'
        vacias_rows += '<td>' + str(cat_nombre) + '</td>'
        vacias_rows += '<td><a href="' + str(cat_url) + '" target="_blank" class="link">Ver</a></td>'
        vacias_rows += '</tr>\n'
    
    # Build rows for error categories
    errores_rows = ""
    for cat in errores:
        cat_status = cat["status"] if cat["status"] else "ERR"
        cat_nombre = cat["nombre"] if cat["nombre"] else "N/A"
        cat_url = cat["url"] if cat["url"] else "#"
        errores_rows += '<tr class="error-row">'
        errores_rows += '<td><span class="badge badge-error">' + str(cat_status) + '</span></td>'
        errores_rows += '<td>' + str(cat_nombre) + '</td>'
        errores_rows += '<td><a href="' + str(cat_url) + '" target="_blank" class="link">Ver</a></td>'
        errores_rows += '</tr>\n'
    
    # Error section HTML
    errores_section = ""
    if errores:
        errores_section = '''
        <div class="section">
            <div class="section-header">
                <span>!</span>
                <h2>URLs con Error</h2>
                <span class="section-count">''' + str(len(errores)) + '''</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>Status</th><th>Categoria</th><th>Accion</th></tr></thead>
                    <tbody>''' + errores_rows + '''</tbody>
                </table>
            </div>
        </div>
        '''
    
    # Empty categories section HTML
    vacias_section = ""
    if vacias:
        vacias_section = '''
        <div class="section">
            <div class="section-header">
                <span>*</span>
                <h2>Categorias Sin Productos</h2>
                <span class="section-count">''' + str(len(vacias)) + '''</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Categoria</th><th>Accion</th></tr></thead>
                    <tbody>''' + vacias_rows + '''</tbody>
                </table>
            </div>
        </div>
        '''
    
    # All OK section
    all_ok_section = ""
    if not errores and not vacias:
        all_ok_section = '''
        <div class="section">
            <div class="empty-state">
                <div class="empty-state-icon">OK</div>
                <p>Todas las categorias estan funcionando correctamente!</p>
            </div>
        </div>
        '''
    
    # Stats color classes
    urls_error_class = "red" if summary["urls_error"] > 0 else "green"
    sin_prod_class = "yellow" if summary["sin_productos"] > 0 else "green"
    
    html = '''<!DOCTYPE html>
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
        :root {
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
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
        }
        .logo { display: flex; align-items: center; gap: 1rem; }
        .logo-icon img {
            max-width: 48px;
        }
        .logo-text h1 { font-size: 1.5rem; font-weight: 700; }
        .logo-text span { font-size: 0.875rem; color: var(--text-muted); }
        .timestamp {
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-secondary);
            background: var(--bg-card);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .status-banner {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem 2rem;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .status-banner.critical { border-color: var(--accent-red); background: rgba(239, 68, 68, 0.1); }
        .status-banner.warning { border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.1); }
        .status-banner.healthy { border-color: var(--accent-green); background: rgba(16, 185, 129, 0.1); }
        .status-indicator {
            width: 12px; height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-banner.critical .status-indicator { background: var(--accent-red); }
        .status-banner.warning .status-indicator { background: var(--accent-yellow); }
        .status-banner.healthy .status-indicator { background: var(--accent-green); }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .status-text { font-size: 1.125rem; font-weight: 600; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s ease;
        }
        .stat-card:hover { background: var(--bg-hover); transform: translateY(-2px); }
        .stat-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stat-value { font-family: var(--font-mono); font-size: 2rem; font-weight: 700; }
        .stat-value.green { color: var(--accent-green); }
        .stat-value.yellow { color: var(--accent-yellow); }
        .stat-value.red { color: var(--accent-red); }
        .stat-value.blue { color: var(--accent-blue); }
        .health-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            text-align: center;
        }
        .health-score {
            font-family: var(--font-mono);
            font-size: 4rem;
            font-weight: 700;
            color: ''' + status_color + ''';
        }
        .health-label { color: var(--text-muted); margin-top: 0.5rem; }
        .section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }
        .section-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .section-header h2 { font-size: 1rem; font-weight: 600; }
        .section-count {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            background: var(--bg-hover);
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            color: var(--text-secondary);
        }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th {
            text-align: left;
            padding: 1rem 1.5rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            background: var(--bg-secondary);
            font-weight: 600;
        }
        td { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); font-size: 0.875rem; }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: var(--bg-hover); }
        .error-row { background: rgba(239, 68, 68, 0.05); }
        .badge {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }
        .badge-id { background: var(--bg-hover); color: var(--text-secondary); }
        .badge-error { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }
        .link { color: var(--accent-blue); text-decoration: none; font-weight: 500; }
        .link:hover { color: var(--text-primary); }
        .empty-state { padding: 3rem; text-align: center; color: var(--text-muted); }
        .empty-state-icon { font-size: 3rem; margin-bottom: 1rem; }
        .footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .header { flex-direction: column; gap: 1rem; text-align: center; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .health-score { font-size: 3rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <div class="logo-icon">
                <img src="https://assets-v3.pcfactory.cl/uploads/e964d6b9-e816-439f-8b97-ad2149772b7b/original/pcfactory-isotipo.svg">
                </div>
                <div class="logo-text">
                    <h1>pc Factory Monitor</h1>
                    <span>Monitoreo de Categorias</span>
                </div>
            </div>
            <div class="timestamp">''' + timestamp_display + '''</div>
        </header>
        
        <div class="status-banner ''' + status_class + '''">
            <div class="status-indicator"></div>
            <span class="status-text">''' + status_text + '''</span>
        </div>
        
        <div class="health-card">
            <div class="health-score">''' + str(summary["health_score"]) + '''%</div>
            <div class="health-label">Health Score (categorias con productos)</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Categorias</div>
                <div class="stat-value blue">''' + str(summary["total_categorias"]) + '''</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLs OK</div>
                <div class="stat-value green">''' + str(summary["urls_ok"]) + '''</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">URLs Error</div>
                <div class="stat-value ''' + urls_error_class + '''">''' + str(summary["urls_error"]) + '''</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Con Productos</div>
                <div class="stat-value green">''' + str(summary["con_productos"]) + '''</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sin Productos</div>
                <div class="stat-value ''' + sin_prod_class + '''">''' + str(summary["sin_productos"]) + '''</div>
            </div>
        </div>
        
        ''' + errores_section + '''
        ''' + vacias_section + '''
        ''' + all_ok_section + '''
        
        <footer class="footer">
            <p>Actualizacion automatica cada 10 minutos - Powered by GitHub Actions</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

# ==============================================================================
# MAIN
# ==============================================================================

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