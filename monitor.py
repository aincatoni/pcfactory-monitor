#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Category Monitor
Verifica el estado de todas las categorias y genera un reporte JSON + HTML + CSV
"""
import csv
import json
import time
import random
import argparse
import concurrent.futures as cf
from datetime import datetime, timezone, timedelta
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
# FUNCIONES DE FECHA/HORA CHILE
# ==============================================================================

def utc_to_chile(dt_utc):
    """Convierte datetime UTC a hora Chile (UTC-3 verano, UTC-4 invierno)."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
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
    
    links = walk_links(nodes)
    print(f"[+] Extraidas {len(links)} categorias unicas")
    
    print(f"[*] Verificando URLs con {workers} workers")
    resultados = []
    
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for item in links:
            url = build_full_url(item["link"])
            fut = pool.submit(probe_with_products, session, item, url, delay_min, delay_max)
            futures[fut] = item
        
        for i, fut in enumerate(cf.as_completed(futures), 1):
            try:
                res = fut.result()
                resultados.append(res)
                status = "✓" if res["ok"] else "✗"
                prod_status = "✓" if res.get("tiene_productos") else "○"
                print(f"  [{i}/{len(links)}] {status} {prod_status} {res['nombre'][:40]}")
            except Exception as e:
                item = futures[fut]
                print(f"  [{i}/{len(links)}] ERROR {item['nombre']}: {e}")
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    urls_ok = sum(1 for r in resultados if r["ok"])
    urls_error = len(resultados) - urls_ok
    con_productos = sum(1 for r in resultados if r.get("tiene_productos"))
    sin_productos = sum(1 for r in resultados if r.get("tiene_productos") == False)
    
    health_score = round((con_productos / len(resultados) * 100), 1) if resultados else 0
    
    errores = [r for r in resultados if not r["ok"]]
    vacias = [r for r in resultados if r.get("tiene_productos") == False]
    
    return {
        "timestamp": timestamp,
        "summary": {
            "total_categorias": len(resultados),
            "urls_ok": urls_ok,
            "urls_error": urls_error,
            "con_productos": con_productos,
            "sin_productos": sin_productos,
            "health_score": health_score,
        },
        "resultados": resultados,
        "categorias_con_errores": errores,
        "categorias_vacias": vacias,
    }

# ==============================================================================
# CSV EXPORT (para Google Sheets IMPORTDATA)
# ==============================================================================

def generate_csv(report: Dict, output_path: Path):
    """
    Genera un CSV con los resultados para importar en Google Sheets.
    Uso en Sheets: =IMPORTDATA("https://aincatoni.github.io/pcfactory-monitor/categories_status.csv")
    """
    resultados = report.get("resultados", [])
    timestamp = report.get("timestamp", "")
    
    # Formato timestamp Chile
    timestamp_chile = format_chile_timestamp(timestamp)
    
    # Ordenar por nombre
    resultados_sorted = sorted(resultados, key=lambda x: x.get('nombre', ''))
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Headers
        writer.writerow([
            'id', 
            'nombre', 
            'link_json', 
            'url', 
            'status_code', 
            'ok', 
            'elapsed_ms', 
            'total_productos',
            'tiene_productos',
            'timestamp'
        ])
        
        # Data rows
        for r in resultados_sorted:
            writer.writerow([
                r.get('id', ''),
                r.get('nombre', ''),
                r.get('link', ''),
                r.get('url', ''),
                r.get('status_code', ''),
                r.get('ok', ''),
                r.get('elapsed_ms', ''),
                r.get('total_productos', ''),
                r.get('tiene_productos', ''),
                timestamp_chile
            ])
    
    print(f"[+] CSV guardado: {output_path}")

def generate_txt(report: Dict, output_path: Path):
    """
    Genera un TXT con formato CSV para Google Sheets IMPORTDATA.
    Los archivos .txt son servidos como text/plain por GitHub Pages,
    lo que permite que IMPORTDATA los lea correctamente.
    
    Uso en Sheets: =IMPORTDATA("https://aincatoni.github.io/pcfactory-monitor/categories_status.txt")
    """
    resultados = report.get("resultados", [])
    timestamp = report.get("timestamp", "")
    timestamp_chile = format_chile_timestamp(timestamp)
    resultados_sorted = sorted(resultados, key=lambda x: x.get('nombre', ''))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('id,nombre,link_json,url,status_code,ok,elapsed_ms,total_productos,tiene_productos,timestamp\n')
        for r in resultados_sorted:
            nombre = str(r.get('nombre', '')).replace('"', '""')
            if ',' in nombre:
                nombre = f'"{nombre}"'
            f.write(f"{r.get('id', '')},{nombre},{r.get('link', '')},{r.get('url', '')},{r.get('status_code', '')},{r.get('ok', '')},{r.get('elapsed_ms', '')},{r.get('total_productos', '')},{r.get('tiene_productos', '')},{timestamp_chile}\n")
    print(f"[+] TXT guardado: {output_path}")

# ==============================================================================
# HTML DASHBOARD GENERATION
# ==============================================================================

def generate_html_dashboard(report: Dict) -> str:
    """Genera el dashboard HTML con los resultados."""
    timestamp = report["timestamp"]
    summary = report["summary"]
    resultados = report["resultados"]
    errores = report["categorias_con_errores"]
    vacias = report["categorias_vacias"]
    
    timestamp_display = format_chile_timestamp(timestamp)
    
    if summary["urls_error"] > 0:
        status_class = "status-error"
        status_text = f"{summary['urls_error']} categorías con errores"
        status_color = "var(--accent-red)"
    elif summary["sin_productos"] > 0:
        status_class = "status-warning"
        status_text = f"{summary['sin_productos']} categorías sin productos"
        status_color = "var(--accent-yellow)"
    else:
        status_class = "status-ok"
        status_text = "Todo OK"
        status_color = "var(--accent-green)"
    
    urls_error_class = "red" if summary["urls_error"] > 0 else "green"
    sin_prod_class = "yellow" if summary["sin_productos"] > 0 else "green"
    
    errores_section = ""
    if errores:
        rows = ""
        for cat in errores:
            rows += f'''<tr class="error-row">
                <td><span class="badge badge-id">{cat.get('id', 'N/A')}</span></td>
                <td>{cat['nombre']}</td>
                <td><span class="badge badge-error">{cat.get('status_code', 'ERR')}</span></td>
                <td><a href="{cat['url']}" target="_blank" class="link">Ver</a></td>
                <td>{cat.get('error', '')[:50]}</td>
            </tr>'''
        errores_section = f'''
        <div class="section">
            <div class="section-header">
                <span>🚨</span>
                <h2>Categorías con Errores</h2>
                <span class="section-count">{len(errores)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Nombre</th><th>Status</th><th>URL</th><th>Error</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>'''
    
    vacias_section = ""
    if vacias:
        rows = ""
        for cat in vacias:
            rows += f'''<tr class="warning-row">
                <td><span class="badge badge-id">{cat.get('id', 'N/A')}</span></td>
                <td>{cat['nombre']}</td>
                <td><span class="badge badge-ok">{cat.get('status_code', 200)}</span></td>
                <td><a href="{cat['url']}" target="_blank" class="link">Ver</a></td>
            </tr>'''
        vacias_section = f'''
        <div class="section">
            <div class="section-header">
                <span>📭</span>
                <h2>Categorías Sin Productos</h2>
                <span class="section-count">{len(vacias)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Nombre</th><th>Status</th><th>URL</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>'''
    
    all_ok_section = ""
    if not errores and not vacias:
        all_ok_section = '''
        <div class="section">
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <p>Todas las categorias estan funcionando correctamente!</p>
            </div>
        </div>'''
    
    all_rows = ""
    for cat in sorted(resultados, key=lambda x: x.get('nombre', '')):
        status_badge = "badge-ok" if cat["ok"] else "badge-error"
        prod_badge = "badge-ok" if cat.get("tiene_productos") else "badge-warning"
        prod_text = cat.get("total_productos", "?")
        row_class = ""
        if not cat["ok"]:
            row_class = "error-row"
        elif not cat.get("tiene_productos"):
            row_class = "warning-row"
        
        all_rows += f'''<tr class="{row_class}">
            <td><span class="badge badge-id">{cat.get('id', 'N/A')}</span></td>
            <td>{cat['nombre']}</td>
            <td><span class="badge {status_badge}">{cat.get('status_code', 'ERR')}</span></td>
            <td><span class="badge {prod_badge}">{prod_text}</span></td>
            <td>{cat.get('elapsed_ms', 0)}ms</td>
            <td><a href="{cat['url']}" target="_blank" class="link">Ver</a></td>
        </tr>'''
    
    all_cats_section = f'''
    <div class="section">
        <div class="section-header">
            <span>📋</span>
            <h2>Todas las Categorías</h2>
            <span class="section-count">{len(resultados)}</span>
            <input type="text" id="filterInput" placeholder="Buscar..." style="margin-left: auto; padding: 0.5rem; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-secondary); color: var(--text-primary);">
        </div>
        <div class="table-container">
            <table id="allCatsTable">
                <thead><tr><th>ID</th><th>Nombre</th><th>Status</th><th>Productos</th><th>Tiempo</th><th>URL</th></tr></thead>
                <tbody>{all_rows}</tbody>
            </table>
        </div>
    </div>'''
    
    html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCFactory Monitor - Categorías</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
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
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: var(--font-sans); background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 1rem; }
        .logo { display: flex; align-items: center; gap: 1rem; }
        .logo-icon { width: 48px; height: 48px; flex-shrink: 0; }
        .logo-icon img { width: 100%; height: 100%; object-fit: contain; }
        .logo-text h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.01em; }
        .logo-text span { color: var(--text-muted); font-size: 0.875rem; }
        .timestamp { font-family: var(--font-mono); font-size: 0.875rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid var(--border); }
        .nav-links { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .nav-link { font-family: var(--font-mono); font-size: 0.875rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.625rem 1rem; border-radius: 8px; border: 1px solid var(--border); text-decoration: none; transition: all 0.2s; }
        .nav-link:hover { background: var(--bg-hover); color: var(--text-primary); }
        .nav-link.active { background: var(--accent-green); color: #000000; border-color: var(--accent-green); font-weight: 500; }
        .status-banner { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; font-weight: 500; }
        .status-ok { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--accent-green); }
        .status-warning { background: rgba(245, 158, 11, 0.15); border: 1px solid var(--accent-yellow); }
        .status-error { background: rgba(239, 68, 68, 0.15); border: 1px solid var(--accent-red); }
        .status-indicator { width: 10px; height: 10px; border-radius: 50%; animation: pulse 2s infinite; }
        .status-ok .status-indicator { background: var(--accent-green); }
        .status-warning .status-indicator { background: var(--accent-yellow); }
        .status-error .status-indicator { background: var(--accent-red); }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 1.5rem; }
        .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; text-align: center; }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .stat-value { font-family: var(--font-mono); font-size: 2rem; font-weight: 700; }
        .stat-value.green { color: var(--accent-green); }
        .stat-value.red { color: var(--accent-red); }
        .stat-value.yellow { color: var(--accent-yellow); }
        .stat-value.blue { color: var(--accent-blue); }
        .health-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 2rem; text-align: center; margin-bottom: 1.5rem; }
        .health-score { font-family: var(--font-mono); font-size: 4rem; font-weight: 700; color: ''' + status_color + '''; }
        .health-label { color: var(--text-muted); margin-top: 0.5rem; }
        .section { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; margin-bottom: 1.5rem; overflow: hidden; }
        .section-header { padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.75rem; }
        .section-header h2 { font-size: 1rem; font-weight: 600; }
        .section-count { font-family: var(--font-mono); font-size: 0.75rem; background: var(--bg-hover); padding: 0.25rem 0.75rem; border-radius: 999px; color: var(--text-secondary); }
        .table-container { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 1rem 1.5rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); background: var(--bg-secondary); font-weight: 600; }
        td { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); font-size: 0.875rem; }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: var(--bg-hover); }
        .error-row { background: rgba(239, 68, 68, 0.05); }
        .warning-row { background: rgba(245, 158, 11, 0.05); }
        .badge { font-family: var(--font-mono); font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 500; }
        .badge-id { background: var(--bg-hover); color: var(--text-secondary); }
        .badge-error { background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }
        .badge-ok { background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }
        .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }
        .link { color: var(--accent-blue); text-decoration: none; font-weight: 500; }
        .link:hover { color: var(--text-primary); }
        .empty-state { padding: 3rem; text-align: center; color: var(--text-muted); }
        .empty-state-icon { font-size: 3rem; margin-bottom: 1rem; }
        .footer { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }
        @media (max-width: 768px) { .container { padding: 1rem; } .header { flex-direction: column; gap: 1rem; text-align: center; } .stats-grid { grid-template-columns: repeat(2, 1fr); } .health-score { font-size: 3rem; } }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <div class="logo-icon"><img src="https://assets-v3.pcfactory.cl/uploads/e964d6b9-e816-439f-8b97-ad2149772b7b/original/pcfactory-isotipo.svg"></div>
                <div class="logo-text"><h1>pc Factory Monitor</h1><span>Monitoreo de Categorias</span></div>
            </div>
            <div class="timestamp">''' + timestamp_display + '''</div>
        </header>
        <div class="nav-links">
            <a href="index.html" class="nav-link active">📦 Categorías</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
        </div>
        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; align-items: center;">
            <span style="color: var(--text-muted); font-size: 0.875rem;">Exportar:</span>
            <a href="categories_status.csv" download style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.4rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); text-decoration: none;">📥 CSV</a>
            <a href="categories_status.txt" target="_blank" style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); background: var(--bg-card); padding: 0.4rem 0.75rem; border-radius: 6px; border: 1px solid var(--border); text-decoration: none;">📄 TXT</a>
            <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.5rem;">Google Sheets: <code style="background: var(--bg-hover); padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.7rem;">=IMPORTDATA("https://aincatoni.github.io/pcfactory-monitor/categories_status.txt")</code></span>
        </div>
        <div class="status-banner ''' + status_class + '''"><div class="status-indicator"></div><span class="status-text">''' + status_text + '''</span></div>
        <div class="health-card"><div class="health-score">''' + str(summary["health_score"]) + '''%</div><div class="health-label">Health Score (categorias con productos)</div></div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-label">Total Categorias</div><div class="stat-value blue">''' + str(summary["total_categorias"]) + '''</div></div>
            <div class="stat-card"><div class="stat-label">URLs OK</div><div class="stat-value green">''' + str(summary["urls_ok"]) + '''</div></div>
            <div class="stat-card"><div class="stat-label">URLs Error</div><div class="stat-value ''' + urls_error_class + '''">''' + str(summary["urls_error"]) + '''</div></div>
            <div class="stat-card"><div class="stat-label">Con Productos</div><div class="stat-value green">''' + str(summary["con_productos"]) + '''</div></div>
            <div class="stat-card"><div class="stat-label">Sin Productos</div><div class="stat-value ''' + sin_prod_class + '''">''' + str(summary["sin_productos"]) + '''</div></div>
        </div>
        ''' + errores_section + vacias_section + all_ok_section + all_cats_section + '''
        <footer class="footer"><p>Actualizacion automatica cada 10 minutos</p><p>Hecho con ❤️ por Ain Cortés Catoni</p></footer>
    </div>
    <script>document.getElementById('filterInput').addEventListener('input', function(e) { const filter = e.target.value.toLowerCase(); document.querySelectorAll('#allCatsTable tbody tr').forEach(row => { row.style.display = row.textContent.toLowerCase().includes(filter) ? '' : 'none'; }); });</script>
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
    
    report = run_monitor(workers=args.workers, delay_min=args.delay_min, delay_max=args.delay_max)
    
    # Guardar JSON
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n[+] JSON guardado: " + str(json_path))
    
    # Guardar HTML
    html_content = generate_html_dashboard(report)
    html_path = output_dir / "index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[+] HTML guardado: " + str(html_path))
    
    # Guardar CSV (para Google Sheets IMPORTDATA)
    csv_path = output_dir / "categories_status.csv"
    generate_csv(report, csv_path)
    
    # Guardar TXT (para Google Sheets IMPORTDATA - mejor compatibilidad)
    txt_path = output_dir / "categories_status.txt"
    generate_txt(report, txt_path)
    
    summary = report["summary"]
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total categorias: {summary['total_categorias']}")
    print(f"URLs OK (200): {summary['urls_ok']}")
    print(f"URLs con error: {summary['urls_error']}")
    print(f"Categorias CON productos: {summary['con_productos']}")
    print(f"Categorias SIN productos: {summary['sin_productos']}")
    
    if report["categorias_vacias"]:
        print("\nCategorias vacias (sin productos):")
        for cat in report["categorias_vacias"]:
            print(f"  - [{cat['id']}] {cat['nombre']}")
    
    print("\n[OK] Monitoreo completado!")

if __name__ == "__main__":
    main()
