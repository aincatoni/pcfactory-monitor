#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Delivery Monitor - Región Metropolitana
Verifica el estado de despacho a todas las comunas y genera un dashboard HTML
"""
import json
import time
import random
import argparse
import unicodedata
import concurrent.futures as cf
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================================================================
# CONFIGURACION
# ==============================================================================

BASE_URL = "https://api.pcfactory.cl/api-delivery-method/v2/delivery/ship"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6_1) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# Comunas de la Región Metropolitana con sus IDs
COMUNAS_RM = [
    (291, "Colina"), (292, "Lampa"), (293, "Tiltil"), (294, "Quilicura"),
    (295, "Pudahuel"), (296, "Conchalí"), (297, "Huechuraba"), (298, "Renca"),
    (299, "Quinta Normal"), (300, "Cerro Navia"), (301, "Lo Prado"), (302, "Independencia"),
    (303, "Recoleta"), (304, "Estación Central"), (305, "Maipú"), (306, "Cerrillos"),
    (307, "Santiago"), (308, "San Bernardo"), (309, "Calera de Tango"), (310, "Buin"),
    (311, "Paine"), (312, "Melipilla"), (313, "Alhué"), (314, "Curacaví"),
    (315, "María Pinto"), (316, "San Pedro"), (317, "Talagante"), (318, "Peñaflor"),
    (319, "El Monte"), (320, "Isla de Maipo"), (321, "Padre Hurtado"), (322, "Ñuñoa"),
    (323, "Providencia"), (324, "Las Condes"), (325, "Vitacura"), (326, "Lo Barnechea"),
    (327, "Peñalolén"), (328, "La Reina"), (329, "La Granja"), (330, "San Joaquín"),
    (331, "Macul"), (332, "La Florida"), (333, "La Cisterna"), (334, "El Bosque"),
    (335, "San Ramón"), (336, "Lo Espejo"), (337, "San Miguel"), (338, "Pedro Aguirre Cerda"),
    (339, "La Pintana"), (340, "Puente Alto"), (341, "Pirque"), (342, "San José de Maipo"),
]

# Provincias por comuna
PROVINCIA_POR_COMUNA = {
    "Cerrillos": "Santiago", "Cerro Navia": "Santiago", "Conchalí": "Santiago", "El Bosque": "Santiago",
    "Estación Central": "Santiago", "Huechuraba": "Santiago", "Independencia": "Santiago", "La Cisterna": "Santiago",
    "La Florida": "Santiago", "La Granja": "Santiago", "La Pintana": "Santiago", "La Reina": "Santiago",
    "Las Condes": "Santiago", "Lo Barnechea": "Santiago", "Lo Espejo": "Santiago", "Lo Prado": "Santiago",
    "Macul": "Santiago", "Maipú": "Santiago", "Ñuñoa": "Santiago", "Pedro Aguirre Cerda": "Santiago",
    "Peñalolén": "Santiago", "Providencia": "Santiago", "Pudahuel": "Santiago", "Quilicura": "Santiago",
    "Quinta Normal": "Santiago", "Recoleta": "Santiago", "Renca": "Santiago", "San Joaquín": "Santiago",
    "San Miguel": "Santiago", "San Ramón": "Santiago", "Santiago": "Santiago", "Vitacura": "Santiago",
    "Pirque": "Cordillera", "Puente Alto": "Cordillera", "San José de Maipo": "Cordillera",
    "Colina": "Chacabuco", "Lampa": "Chacabuco", "Tiltil": "Chacabuco",
    "Buin": "Maipo", "Calera de Tango": "Maipo", "Paine": "Maipo", "San Bernardo": "Maipo",
    "Alhué": "Melipilla", "Curacaví": "Melipilla", "María Pinto": "Melipilla", "Melipilla": "Melipilla", "San Pedro": "Melipilla",
    "El Monte": "Talagante", "Isla de Maipo": "Talagante", "Padre Hurtado": "Talagante", "Peñaflor": "Talagante", "Talagante": "Talagante",
}

# Ciudades para matchear con comunas (las más comunes de la RM)
CIUDADES_RM = [
    (1, "Santiago"), (437, "Buin"), (440, "Colina"), (441, "Curacavi"),
    (442, "El Monte"), (444, "Lampa"), (449, "Melipilla"), (450, "Padre Hurtado"),
    (452, "Penaflor"), (456, "Talagante"), (458, "Calera de Tango"), (1067, "Tiltil"),
    (1331, "Alhue"), (1343, "San Pedro de Melipilla"), (439, "Cajon del Maipo"),
    (443, "Isla de Maipo"), (451, "Paine"), (453, "Pirque"), (454, "San Jose de Maipo"),
    (2474, "Chicureo"), (448, "Maria Pinto"),
]

# ==============================================================================
# UTILIDADES
# ==============================================================================

def nfd_lower(s: str) -> str:
    """Normaliza string para comparación (sin acentos, lowercase)"""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()

def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json",
        "Accept-Language": "es-CL,es;q=0.9",
    })
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def polite_pause(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

# ==============================================================================
# API CALLS
# ==============================================================================

def build_url(tienda_id: int, ciudad_id: int, id_comuna: int, cantidad: int, id_producto: int, total: int) -> str:
    return f"{BASE_URL}/{tienda_id}/{ciudad_id}/{id_comuna}/web?cantidad={cantidad}&id_producto={id_producto}&total={total}"

def call_endpoint(session: requests.Session, url: str, timeout: int = 15) -> Tuple[int, Optional[Dict]]:
    try:
        r = session.get(url, timeout=timeout)
        return r.status_code, (r.json() if r.content else None)
    except Exception:
        return 0, None

def parse_payload(payload: Dict) -> Tuple[str, Optional[str], Optional[int], Optional[str]]:
    """Retorna (estado, fecha_entrega, dias_entrega, transporte)"""
    if not isinstance(payload, dict):
        return ("No disponible", None, None, None)
    if str(payload.get("codigo")) != "0":
        return ("No disponible", None, None, None)
    tarifas = (payload.get("resultado") or {}).get("tarifas") or []
    if not tarifas:
        return ("No disponible", None, None, None)
    t0 = tarifas[0]
    return ("Disponible", t0.get("fecha_entrega"), t0.get("dias_entrega"), t0.get("transporte"))

def find_best_city(session: requests.Session, id_comuna: int, comuna: str, 
                   tienda_id: int, cantidad: int, producto: int, total: int,
                   delay_min: float, delay_max: float) -> Dict[str, Any]:
    """Prueba diferentes ciudades para encontrar una que tenga disponibilidad"""
    target = nfd_lower(comuna)
    
    # Ordenar ciudades: primero las que matchean el nombre, luego Santiago, luego el resto
    ordered = []
    for cid, cname in CIUDADES_RM:
        if nfd_lower(cname) == target:
            ordered.insert(0, (cid, cname))
        elif cid == 1:  # Santiago como fallback principal
            ordered.insert(1 if ordered else 0, (cid, cname))
        else:
            ordered.append((cid, cname))
    
    # Probar en orden hasta encontrar disponibilidad
    for ciudad_id, ciudad_nombre in ordered[:5]:  # Limitar a 5 intentos
        polite_pause(delay_min, delay_max)
        url = build_url(tienda_id, ciudad_id, id_comuna, cantidad, producto, total)
        http_code, payload = call_endpoint(session, url)
        estado, fecha, dias, transporte = parse_payload(payload or {})
        
        if estado == "Disponible":
            return {
                "estado": estado,
                "fecha_entrega": fecha,
                "dias_entrega": dias,
                "transporte": transporte,
                "ciudad_id": ciudad_id,
                "ciudad_nombre": ciudad_nombre,
                "http_code": http_code,
                "url": url,
            }
    
    # Si ninguna funcionó, retornar el último intento
    return {
        "estado": "No disponible",
        "fecha_entrega": None,
        "dias_entrega": None,
        "transporte": None,
        "ciudad_id": ordered[0][0] if ordered else 1,
        "ciudad_nombre": ordered[0][1] if ordered else "Santiago",
        "http_code": http_code if 'http_code' in dir() else 0,
        "url": url if 'url' in dir() else "",
    }

def check_comuna(session: requests.Session, id_comuna: int, comuna: str,
                 tienda_id: int, cantidad: int, producto: int, total: int,
                 delay_min: float, delay_max: float) -> Dict[str, Any]:
    """Verifica disponibilidad de despacho para una comuna"""
    result = find_best_city(session, id_comuna, comuna, tienda_id, cantidad, producto, total, delay_min, delay_max)
    
    return {
        "id_comuna": id_comuna,
        "comuna": comuna,
        "provincia": PROVINCIA_POR_COMUNA.get(comuna, ""),
        **result
    }

# ==============================================================================
# MONITOR PRINCIPAL
# ==============================================================================

def run_delivery_monitor(producto: int, total: int, tienda_id: int = 11, cantidad: int = 1,
                         workers: int = 3, delay_min: float = 0.3, delay_max: float = 0.7) -> Dict:
    session = create_session()
    
    print(f"[*] Producto: {producto} | Total: ${total:,} | Tienda: {tienda_id}")
    print(f"[*] Comunas a verificar: {len(COMUNAS_RM)}")
    
    results = []
    
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                check_comuna, session, id_comuna, comuna,
                tienda_id, cantidad, producto, total, delay_min, delay_max
            ): (id_comuna, comuna)
            for id_comuna, comuna in COMUNAS_RM
        }
        
        for i, future in enumerate(cf.as_completed(future_map), 1):
            try:
                result = future.result()
                results.append(result)
                
                status = "[OK]" if result["estado"] == "Disponible" else "[--]"
                dias = result.get("dias_entrega", "?")
                print(f"  {status} {i}/{len(COMUNAS_RM)} {result['comuna']}: {dias} días")
                
            except Exception as e:
                id_comuna, comuna = future_map[future]
                print(f"  [ERR] {comuna}: {e}")
                results.append({
                    "id_comuna": id_comuna,
                    "comuna": comuna,
                    "provincia": PROVINCIA_POR_COMUNA.get(comuna, ""),
                    "estado": "Error",
                    "fecha_entrega": None,
                    "dias_entrega": None,
                    "transporte": None,
                    "ciudad_id": None,
                    "ciudad_nombre": None,
                    "http_code": 0,
                    "url": "",
                    "error": str(e),
                })
    
    # Ordenar por provincia y comuna
    results.sort(key=lambda x: (x.get("provincia", ""), x.get("comuna", "")))
    
    # Calcular estadísticas
    disponibles = [r for r in results if r["estado"] == "Disponible"]
    no_disponibles = [r for r in results if r["estado"] == "No disponible"]
    errores = [r for r in results if r["estado"] == "Error"]
    
    # Distribución por días
    dias_dist = {}
    for r in disponibles:
        dias = r.get("dias_entrega")
        if dias is not None:
            dias_dist[dias] = dias_dist.get(dias, 0) + 1
    
    # Calcular promedio de días
    dias_values = [r["dias_entrega"] for r in disponibles if r.get("dias_entrega") is not None]
    promedio_dias = round(sum(dias_values) / len(dias_values), 1) if dias_values else 0
    
    now = datetime.now(timezone.utc)
    
    summary = {
        "total_comunas": len(results),
        "disponibles": len(disponibles),
        "no_disponibles": len(no_disponibles),
        "errores": len(errores),
        "promedio_dias": promedio_dias,
        "dias_distribucion": dias_dist,
        "cobertura_pct": round(len(disponibles) / len(results) * 100, 1) if results else 0,
    }
    
    return {
        "timestamp": now.isoformat(),
        "producto": producto,
        "total": total,
        "tienda_id": tienda_id,
        "cantidad": cantidad,
        "summary": summary,
        "comunas": results,
        "no_disponibles": no_disponibles,
        "errores": errores,
    }

# ==============================================================================
# GENERADOR HTML
# ==============================================================================

def generate_html_dashboard(report: Dict) -> str:
    summary = report["summary"]
    comunas = report["comunas"]
    no_disponibles = report["no_disponibles"]
    errores = report.get("errores", [])
    
    # Timestamp
    try:
        ts = datetime.fromisoformat(report["timestamp"].replace("Z", "+00:00"))
        timestamp_display = ts.strftime("%d/%m/%Y %H:%M:%S") + " UTC"
    except:
        timestamp_display = report["timestamp"]
    
    # Status banner
    if errores:
        status_class = "critical"
        status_text = f"{len(errores)} comunas con error"
        status_color = "#ef4444"
    elif no_disponibles:
        status_class = "warning"
        status_text = f"{len(no_disponibles)} comunas sin despacho"
        status_color = "#f59e0b"
    else:
        status_class = "healthy"
        status_text = "Despacho disponible en todas las comunas"
        status_color = "#10b981"
    
    # Filas de comunas sin disponibilidad
    no_disp_rows = ""
    for c in no_disponibles:
        no_disp_rows += f'''<tr>
            <td><span class="badge badge-id">{c["id_comuna"]}</span></td>
            <td>{c["comuna"]}</td>
            <td>{c.get("provincia", "-")}</td>
        </tr>\n'''
    
    # Filas de errores
    error_rows = ""
    for c in errores:
        error_rows += f'''<tr class="error-row">
            <td><span class="badge badge-error">{c.get("http_code", "ERR")}</span></td>
            <td>{c["comuna"]}</td>
            <td>{c.get("error", "-")[:50]}</td>
        </tr>\n'''
    
    # Sección sin disponibilidad
    no_disp_section = ""
    if no_disponibles:
        no_disp_section = f'''
        <div class="section">
            <div class="section-header">
                <span>⚠</span>
                <h2>Comunas Sin Despacho</h2>
                <span class="section-count">{len(no_disponibles)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>ID</th><th>Comuna</th><th>Provincia</th></tr></thead>
                    <tbody>{no_disp_rows}</tbody>
                </table>
            </div>
        </div>
        '''
    
    # Sección errores
    error_section = ""
    if errores:
        error_section = f'''
        <div class="section">
            <div class="section-header">
                <span>!</span>
                <h2>Errores de Conexión</h2>
                <span class="section-count">{len(errores)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead><tr><th>Status</th><th>Comuna</th><th>Error</th></tr></thead>
                    <tbody>{error_rows}</tbody>
                </table>
            </div>
        </div>
        '''
    
    # Tabla completa de comunas
    comunas_rows = ""
    for c in comunas:
        dias = c.get("dias_entrega")
        if dias is not None:
            if dias <= 1:
                dias_class = "green"
                dias_badge = "badge-ok"
            elif dias <= 3:
                dias_class = "blue"
                dias_badge = "badge-id"
            else:
                dias_class = "yellow"
                dias_badge = "badge-warn"
            dias_display = f'<span class="badge {dias_badge}">{dias} día{"s" if dias != 1 else ""}</span>'
        else:
            dias_class = "red"
            dias_display = '<span class="badge badge-error">-</span>'
        
        estado_badge = "badge-ok" if c["estado"] == "Disponible" else "badge-error"
        
        comunas_rows += f'''<tr>
            <td><span class="badge badge-id">{c["id_comuna"]}</span></td>
            <td>{c["comuna"]}</td>
            <td>{c.get("provincia", "-")}</td>
            <td>{dias_display}</td>
            <td>{c.get("fecha_entrega", "-") or "-"}</td>
            <td>{c.get("transporte", "-") or "-"}</td>
            <td><span class="badge {estado_badge}">{c["estado"]}</span></td>
        </tr>\n'''
    
    # Distribución de días (mini chart)
    dias_dist = summary.get("dias_distribucion", {})
    dias_chart = ""
    if dias_dist:
        max_count = max(dias_dist.values()) if dias_dist else 1
        for dias in sorted(dias_dist.keys()):
            count = dias_dist[dias]
            pct = (count / max_count) * 100
            dias_chart += f'''
            <div class="dist-bar">
                <span class="dist-label">{dias}d</span>
                <div class="dist-track">
                    <div class="dist-fill" style="width: {pct}%"></div>
                </div>
                <span class="dist-count">{count}</span>
            </div>'''
    
    # Stats color classes
    no_disp_class = "red" if summary["no_disponibles"] > 0 else "green"
    error_class = "red" if summary["errores"] > 0 else "green"
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="600">
    <title>PCFactory Delivery Monitor - RM</title>
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
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .logo {{ display: flex; align-items: center; gap: 1rem; }}
        .logo-icon {{ width: 48px; height: 48px; }}
        .logo-icon img {{ width: 100%; height: 100%; object-fit: contain; }}
        .logo-text h1 {{ font-size: 1.5rem; font-weight: 700; }}
        .logo-text span {{ font-size: 0.875rem; color: var(--text-muted); }}
        .timestamp {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-muted);
            background: var(--bg-card);
            padding: 0.5rem 1rem;
            border-radius: 8px;
        }}
        .nav-links {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .nav-link {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--accent-blue);
            text-decoration: none;
            padding: 0.5rem 1rem;
            background: var(--bg-card);
            border-radius: 8px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }}
        .nav-link:hover {{ background: var(--bg-hover); }}
        .nav-link.active {{ background: var(--accent-blue); color: white; }}
        .status-banner {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            font-weight: 500;
        }}
        .status-banner.healthy {{ background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); }}
        .status-banner.warning {{ background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); }}
        .status-banner.critical {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }}
        .status-indicator {{
            width: 10px; height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        .healthy .status-indicator {{ background: var(--accent-green); }}
        .warning .status-indicator {{ background: var(--accent-yellow); }}
        .critical .status-indicator {{ background: var(--accent-red); }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
        .stat-card:hover {{ background: var(--bg-hover); transform: translateY(-2px); }}
        .stat-label {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-value {{ font-family: var(--font-mono); font-size: 2rem; font-weight: 700; }}
        .stat-value.green {{ color: var(--accent-green); }}
        .stat-value.yellow {{ color: var(--accent-yellow); }}
        .stat-value.red {{ color: var(--accent-red); }}
        .stat-value.blue {{ color: var(--accent-blue); }}
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
            color: {status_color};
        }}
        .health-label {{ color: var(--text-muted); margin-top: 0.5rem; }}
        .dist-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .dist-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }}
        .dist-bar {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }}
        .dist-label {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            width: 30px;
            color: var(--text-muted);
        }}
        .dist-track {{
            flex: 1;
            height: 20px;
            background: var(--bg-secondary);
            border-radius: 4px;
            overflow: hidden;
        }}
        .dist-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .dist-count {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            width: 30px;
            text-align: right;
            color: var(--text-secondary);
        }}
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
        .section-header h2 {{ font-size: 1rem; font-weight: 600; }}
        .section-count {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            background: var(--bg-hover);
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            color: var(--text-secondary);
        }}
        .table-container {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
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
        td {{ padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); font-size: 0.875rem; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: var(--bg-hover); }}
        .error-row {{ background: rgba(239, 68, 68, 0.05); }}
        .badge {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        .badge-id {{ background: var(--bg-hover); color: var(--text-secondary); }}
        .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .badge-warn {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}
        .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
        .product-info {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            background: var(--bg-secondary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .footer {{ text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .health-score {{ font-size: 3rem; }}
        }}
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
                    <span>Despacho Región Metropolitana</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <div class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link active">🚚 Despacho RM</a>
        </div>
        
        <div class="product-info">
            Producto: {report["producto"]} | Total: ${report["total"]:,} | Cantidad: {report["cantidad"]}
        </div>
        
        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>
        
        <div class="health-card">
            <div class="health-score">{summary["cobertura_pct"]}%</div>
            <div class="health-label">Cobertura de Despacho (comunas con disponibilidad)</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Comunas</div>
                <div class="stat-value blue">{summary["total_comunas"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Disponibles</div>
                <div class="stat-value green">{summary["disponibles"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Sin Despacho</div>
                <div class="stat-value {no_disp_class}">{summary["no_disponibles"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Promedio Días</div>
                <div class="stat-value blue">{summary["promedio_dias"]}</div>
            </div>
        </div>
        
        <div class="dist-container">
            <div class="dist-title">Distribución por Días de Entrega</div>
            {dias_chart if dias_chart else '<p style="color: var(--text-muted);">Sin datos</p>'}
        </div>
        
        {error_section}
        {no_disp_section}
        
        <div class="section">
            <div class="section-header">
                <span>📍</span>
                <h2>Todas las Comunas</h2>
                <span class="section-count">{len(comunas)}</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Comuna</th>
                            <th>Provincia</th>
                            <th>Días</th>
                            <th>Fecha Entrega</th>
                            <th>Transporte</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>{comunas_rows}</tbody>
                </table>
            </div>
        </div>
        
        <footer class="footer">
            <p>Actualización automática cada 10 minutos</p>
            <p>Hecho con ❤️ por Ain Catoni</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="PCFactory Delivery Monitor - RM")
    parser.add_argument("--producto", type=int, required=True, help="ID del producto")
    parser.add_argument("--total", type=int, required=True, help="Total del carrito")
    parser.add_argument("--tienda", type=int, default=11, help="ID tienda (default: 11)")
    parser.add_argument("--cantidad", type=int, default=1, help="Cantidad (default: 1)")
    parser.add_argument("--workers", type=int, default=3, help="Workers paralelos")
    parser.add_argument("--delay-min", type=float, default=0.3)
    parser.add_argument("--delay-max", type=float, default=0.7)
    parser.add_argument("--output-dir", type=str, default="./output")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Delivery Monitor - Región Metropolitana")
    print("=" * 60)
    
    report = run_delivery_monitor(
        producto=args.producto,
        total=args.total,
        tienda_id=args.tienda,
        cantidad=args.cantidad,
        workers=args.workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
    )
    
    # Guardar JSON
    json_path = output_dir / "delivery_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[+] JSON guardado: {json_path}")
    
    # Guardar HTML
    html_content = generate_html_dashboard(report)
    html_path = output_dir / "delivery.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] HTML guardado: {html_path}")
    
    # Resumen
    summary = report["summary"]
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total comunas: {summary['total_comunas']}")
    print(f"Con despacho: {summary['disponibles']}")
    print(f"Sin despacho: {summary['no_disponibles']}")
    print(f"Cobertura: {summary['cobertura_pct']}%")
    print(f"Promedio días: {summary['promedio_dias']}")
    
    if report["no_disponibles"]:
        print("\nComunas sin despacho:")
        for c in report["no_disponibles"]:
            print(f"  - [{c['id_comuna']}] {c['comuna']}")
    
    print("\n[OK] Monitoreo completado!")

if __name__ == "__main__":
    main()
