#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Delivery Monitor - Nacional
Verifica el estado de despacho a todas las comunas de Chile y genera un dashboard HTML
"""
import json
import time
import random
import argparse
import csv
import concurrent.futures as cf
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
# CONFIGURACION
# ==============================================================================

# Endpoint para verificar disponibilidad de despacho
DELIVERY_URL = "https://api.pcfactory.cl/api-delivery-method/v2/delivery/ship"

# Endpoint para obtener costo del despacho (POST)
COSTO_URL = "https://api.pcfactory.cl/pcfactory-services-carro-compra/v1/carro/entrega/despacho"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6_1) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

# Nombres de regiones
REGIONES = {
    1: "Tarapacá",
    2: "Antofagasta", 
    3: "Atacama",
    4: "Coquimbo",
    5: "Valparaíso",
    6: "O'Higgins",
    7: "Maule",
    8: "Biobío",
    9: "Araucanía",
    10: "Los Lagos",
    11: "Aysén",
    12: "Magallanes",
    13: "Metropolitana",
    14: "Los Ríos",
    15: "Arica y Parinacota",
    16: "Ñuble",
}

# ==============================================================================
# CARGA DE DATOS
# ==============================================================================

def load_ciudades(path: str) -> Dict[int, Dict]:
    """Carga ciudades: {id_ciudad: {nombre, id_region}}"""
    ciudades = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                cid = int(row["id_ciudad"])
                ciudades[cid] = {
                    "nombre": row["ciudad"].strip(),
                    "id_region": int(row["id_region"]),
                }
            except (ValueError, KeyError):
                continue
    return ciudades

def load_comunas(path: str) -> Dict[int, Dict]:
    """Carga comunas: {id_comuna: {nombre, id_region, despacho}}"""
    comunas = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                cid = int(row["id_comuna"])
                comunas[cid] = {
                    "nombre": row["comuna"].strip(),
                    "id_region": int(row["id_region"]),
                    "despacho": int(row.get("despacho", 1)),
                }
            except (ValueError, KeyError):
                continue
    return comunas

def load_ciudad_comuna(path: str) -> Dict[int, int]:
    """Carga relación comuna->ciudad: {id_comuna: id_ciudad}"""
    relacion = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                id_comuna = int(row["id_comuna"])
                id_ciudad = int(row["id_ciudad"])
                # Si hay múltiples ciudades para una comuna, quedarse con la primera
                if id_comuna not in relacion:
                    relacion[id_comuna] = id_ciudad
            except (ValueError, KeyError):
                continue
    return relacion

# ==============================================================================
# UTILIDADES
# ==============================================================================

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
    adapter = HTTPAdapter(max_retries=retry, pool_connections=15, pool_maxsize=15)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def polite_pause(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))

def formato_clp(numero: int) -> str:
    """Formatea número al estilo chileno (punto como separador de miles)"""
    if numero is None:
        return "0"
    # Convertir a int para eliminar decimales (pesos chilenos no usan decimales)
    return f"{int(numero):,}".replace(",", ".")

# ==============================================================================
# API CALLS
# ==============================================================================

def build_url(tienda_id: int, ciudad_id: int, id_comuna: int, cantidad: int, id_producto: int, total: int) -> str:
    return f"{DELIVERY_URL}/{tienda_id}/{ciudad_id}/{id_comuna}/web?cantidad={cantidad}&id_producto={id_producto}&total={total}"

def call_endpoint(session: requests.Session, url: str, timeout: int = 15) -> Tuple[int, Optional[Dict]]:
    try:
        r = session.get(url, timeout=timeout)
        return r.status_code, (r.json() if r.content else None)
    except Exception:
        return 0, None

def get_costo_despacho(session: requests.Session, producto_id: int, cantidad: int, 
                       ciudad_nombre: str, comuna_nombre: str, timeout: int = 15) -> Tuple[Optional[int], bool]:
    """
    Obtiene el costo del despacho usando el endpoint del carro de compra.
    Retorna (costo, gratis)
    """
    try:
        payload = {
            "items": [{"id": producto_id, "cantidad": cantidad, "origin": "PCF", "empresa": "PCFACTORY"}],
            "ciudad": ciudad_nombre.upper(),
            "comuna": comuna_nombre.upper()
        }
        r = session.post(COSTO_URL, json=payload, timeout=timeout)
        if r.status_code != 200:
            return None, False
        
        data = r.json()
        opciones = data.get("opciones") or []
        if not opciones:
            return None, False
        
        costo = opciones[0].get("costo")
        gratis = costo == 0 if costo is not None else False
        return costo, gratis
    except Exception:
        return None, False

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

def check_comuna(session: requests.Session, id_comuna: int, comuna_data: Dict,
                 id_ciudad: int, ciudad_data: Dict,
                 tienda_id: int, cantidad: int, producto: int, total: int,
                 delay_min: float, delay_max: float) -> Dict[str, Any]:
    """Verifica disponibilidad de despacho para una comuna y obtiene el costo"""
    polite_pause(delay_min, delay_max)
    
    # 1. Verificar disponibilidad con el endpoint original
    url = build_url(tienda_id, id_ciudad, id_comuna, cantidad, producto, total)
    http_code, payload = call_endpoint(session, url)
    estado, fecha, dias, transporte = parse_payload(payload or {})
    
    # 2. Si está disponible, obtener el costo con el nuevo endpoint
    precio = None
    gratis = False
    if estado == "Disponible":
        ciudad_nombre = ciudad_data["nombre"] if ciudad_data else "SANTIAGO"
        comuna_nombre = comuna_data["nombre"]
        polite_pause(delay_min * 0.5, delay_max * 0.5)  # Pausa más corta para segunda llamada
        precio, gratis = get_costo_despacho(session, producto, cantidad, ciudad_nombre, comuna_nombre)
    
    return {
        "id_comuna": id_comuna,
        "comuna": comuna_data["nombre"],
        "id_region": comuna_data["id_region"],
        "region": REGIONES.get(comuna_data["id_region"], f"Región {comuna_data['id_region']}"),
        "id_ciudad": id_ciudad,
        "ciudad": ciudad_data["nombre"] if ciudad_data else "N/A",
        "estado": estado,
        "fecha_entrega": fecha,
        "dias_entrega": dias,
        "transporte": transporte,
        "precio_despacho": precio,
        "despacho_gratis": gratis,
        "http_code": http_code,
        "url": url,
    }

# ==============================================================================
# MONITOR PRINCIPAL
# ==============================================================================

def run_delivery_monitor(producto: int, total: int, 
                         ciudades_path: str, comunas_path: str, relacion_path: str,
                         tienda_id: int = 11, cantidad: int = 1,
                         workers: int = 5, delay_min: float = 0.2, delay_max: float = 0.5,
                         region_filter: Optional[int] = None) -> Dict:
    
    # Cargar datos
    print("[*] Cargando datos...")
    ciudades = load_ciudades(ciudades_path)
    comunas = load_comunas(comunas_path)
    relacion = load_ciudad_comuna(relacion_path)
    
    print(f"    Ciudades: {len(ciudades)}")
    print(f"    Comunas: {len(comunas)}")
    print(f"    Relaciones: {len(relacion)}")
    
    # Filtrar por región si se especifica
    if region_filter:
        comunas = {k: v for k, v in comunas.items() if v["id_region"] == region_filter}
        print(f"    Filtrado a región {region_filter}: {len(comunas)} comunas")
    
    session = create_session()
    
    print(f"\n[*] Producto: {producto} | Total: ${total:,} | Tienda: {tienda_id}")
    print(f"[*] Comunas a verificar: {len(comunas)}")
    
    results = []
    
    # Preparar tareas
    tasks = []
    for id_comuna, comuna_data in comunas.items():
        id_ciudad = relacion.get(id_comuna)
        if id_ciudad is None:
            print(f"    [WARN] Comuna {id_comuna} sin ciudad asignada, usando Santiago")
            id_ciudad = 1
        ciudad_data = ciudades.get(id_ciudad, {"nombre": "Desconocida", "id_region": 0})
        tasks.append((id_comuna, comuna_data, id_ciudad, ciudad_data))
    
    # Ejecutar en paralelo
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(
                check_comuna, session, id_comuna, comuna_data, id_ciudad, ciudad_data,
                tienda_id, cantidad, producto, total, delay_min, delay_max
            ): (id_comuna, comuna_data)
            for id_comuna, comuna_data, id_ciudad, ciudad_data in tasks
        }
        
        for i, future in enumerate(cf.as_completed(future_map), 1):
            try:
                result = future.result()
                results.append(result)
                
                status = "OK" if result["estado"] == "Disponible" else "--"
                dias = result.get("dias_entrega", "?")
                print(f"  [{status}] {i}/{len(tasks)} {result['comuna']}: {dias} días")
                
            except Exception as e:
                id_comuna, comuna_data = future_map[future]
                print(f"  [ERR] {comuna_data['nombre']}: {e}")
                results.append({
                    "id_comuna": id_comuna,
                    "comuna": comuna_data["nombre"],
                    "id_region": comuna_data["id_region"],
                    "region": REGIONES.get(comuna_data["id_region"], ""),
                    "id_ciudad": None,
                    "ciudad": "Error",
                    "estado": "Error",
                    "fecha_entrega": None,
                    "dias_entrega": None,
                    "transporte": None,
                    "http_code": 0,
                    "url": "",
                    "error": str(e),
                })
    
    # Ordenar por región y comuna
    results.sort(key=lambda x: (x.get("id_region", 0), x.get("comuna", "")))
    
    # Calcular estadísticas globales
    disponibles = [r for r in results if r["estado"] == "Disponible"]
    no_disponibles = [r for r in results if r["estado"] == "No disponible"]
    errores = [r for r in results if r["estado"] == "Error"]
    
    # Estadísticas de precio
    con_precio = [r for r in disponibles if r.get("precio_despacho") is not None]
    gratis_count = len([r for r in disponibles if r.get("despacho_gratis")])
    precios = [r["precio_despacho"] for r in con_precio if r["precio_despacho"] > 0]
    precio_promedio = round(sum(precios) / len(precios)) if precios else 0
    precio_min = min(precios) if precios else 0
    precio_max = max(precios) if precios else 0
    
    # Estadísticas por región
    stats_por_region = {}
    for r in results:
        reg_id = r["id_region"]
        if reg_id not in stats_por_region:
            stats_por_region[reg_id] = {
                "nombre": REGIONES.get(reg_id, f"Región {reg_id}"),
                "total": 0,
                "disponibles": 0,
                "no_disponibles": 0,
                "errores": 0,
                "dias_sum": 0,
                "dias_count": 0,
                "precio_sum": 0,
                "precio_count": 0,
                "gratis_count": 0,
            }
        stats_por_region[reg_id]["total"] += 1
        if r["estado"] == "Disponible":
            stats_por_region[reg_id]["disponibles"] += 1
            if r.get("dias_entrega") is not None:
                stats_por_region[reg_id]["dias_sum"] += r["dias_entrega"]
                stats_por_region[reg_id]["dias_count"] += 1
            if r.get("precio_despacho") is not None and r["precio_despacho"] > 0:
                stats_por_region[reg_id]["precio_sum"] += r["precio_despacho"]
                stats_por_region[reg_id]["precio_count"] += 1
            if r.get("despacho_gratis"):
                stats_por_region[reg_id]["gratis_count"] += 1
        elif r["estado"] == "No disponible":
            stats_por_region[reg_id]["no_disponibles"] += 1
        else:
            stats_por_region[reg_id]["errores"] += 1
    
    # Calcular promedios y porcentajes por región
    for reg_id, stats in stats_por_region.items():
        stats["cobertura_pct"] = round(stats["disponibles"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        stats["promedio_dias"] = round(stats["dias_sum"] / stats["dias_count"], 1) if stats["dias_count"] > 0 else 0
        stats["precio_promedio"] = round(stats["precio_sum"] / stats["precio_count"]) if stats["precio_count"] > 0 else 0
    
    # Distribución por días (global)
    dias_dist = {}
    for r in disponibles:
        dias = r.get("dias_entrega")
        if dias is not None:
            dias_dist[dias] = dias_dist.get(dias, 0) + 1
    
    # Promedio global
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
        "total_regiones": len(stats_por_region),
        "despacho_gratis": gratis_count,
        "precio_promedio": precio_promedio,
        "precio_min": precio_min,
        "precio_max": precio_max,
    }
    
    return {
        "timestamp": now.isoformat(),
        "producto": producto,
        "total": total,
        "tienda_id": tienda_id,
        "cantidad": cantidad,
        "summary": summary,
        "stats_por_region": stats_por_region,
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
    stats_por_region = report.get("stats_por_region", {})
    
    # Timestamp - usar hora Chile
    timestamp_display = format_chile_timestamp(report.get("timestamp", ""))
    
    # Status banner
    if errores:
        status_class = "critical"
        status_text = f"{len(errores)} comunas con error"
        status_color = "#ef4444"
    elif len(no_disponibles) > 10:
        status_class = "warning"
        status_text = f"{len(no_disponibles)} comunas sin despacho"
        status_color = "#f59e0b"
    elif no_disponibles:
        status_class = "warning"
        status_text = f"{len(no_disponibles)} comunas sin despacho"
        status_color = "#f59e0b"
    else:
        status_class = "healthy"
        status_text = "Despacho disponible en todas las comunas"
        status_color = "#10b981"
    
    # Cards por región
    region_cards = ""
    for reg_id in sorted(stats_por_region.keys()):
        stats = stats_por_region[reg_id]
        cob = stats["cobertura_pct"]
        if cob >= 95:
            cob_class = "green"
        elif cob >= 80:
            cob_class = "yellow"
        else:
            cob_class = "red"
        
        region_cards += f'''
        <div class="region-card" data-region="{reg_id}">
            <div class="region-name">{stats["nombre"]}</div>
            <div class="region-cob {cob_class}">{cob}%</div>
            <div class="region-stats">
                <span>{stats["disponibles"]}/{stats["total"]}</span>
                <span>~{stats["promedio_dias"]}d</span>
            </div>
        </div>'''
    
    # Filas de comunas sin disponibilidad
    no_disp_rows = ""
    for c in no_disponibles:
        no_disp_rows += f'''<tr>
            <td><span class="badge badge-id">{c["id_comuna"]}</span></td>
            <td>{c["comuna"]}</td>
            <td>{c.get("region", "-")}</td>
            <td>{c.get("ciudad", "-")}</td>
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
                    <thead><tr><th>ID</th><th>Comuna</th><th>Región</th><th>Ciudad</th></tr></thead>
                    <tbody>{no_disp_rows}</tbody>
                </table>
            </div>
        </div>
        '''
    
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
    
    # Tabla completa de comunas (agrupada por región)
    comunas_rows = ""
    current_region = None
    for c in comunas:
        # Header de región
        if c.get("id_region") != current_region:
            current_region = c.get("id_region")
            region_name = REGIONES.get(current_region, f"Región {current_region}")
            comunas_rows += f'''<tr class="region-header-row">
                <td colspan="8"><strong>{region_name}</strong></td>
            </tr>\n'''
        
        dias = c.get("dias_entrega")
        if dias is not None:
            if dias <= 2:
                dias_badge = "badge-ok"
            elif dias <= 5:
                dias_badge = "badge-id"
            else:
                dias_badge = "badge-warn"
            dias_display = f'<span class="badge {dias_badge}">{dias}d</span>'
        else:
            dias_display = '<span class="badge badge-error">-</span>'
        
        # Precio de despacho
        precio = c.get("precio_despacho")
        gratis = c.get("despacho_gratis")
        if gratis:
            precio_display = '<span class="badge badge-ok">Gratis</span>'
        elif precio is not None and precio > 0:
            precio_display = f'<span class="badge badge-id">${formato_clp(precio)}</span>'
        elif c["estado"] == "Disponible":
            # Disponible pero sin info de precio - mostrar en gris
            precio_display = '<span class="badge badge-id">N/D</span>'
        else:
            # No disponible
            precio_display = '<span class="badge badge-muted">-</span>'
        
        estado_badge = "badge-ok" if c["estado"] == "Disponible" else "badge-error"

        # Valores raw para ordenamiento
        dias_value = dias if dias is not None else 999
        precio_value = precio if precio is not None else 999999
        transporte_value = c.get("transporte", "") or ""

        comunas_rows += f'''<tr data-region="{c.get("id_region", 0)}" data-id="{c["id_comuna"]}" data-comuna="{c["comuna"]}" data-dias="{dias_value}" data-precio="{precio_value}" data-estado="{c["estado"]}" data-gratis="{gratis}" data-transporte="{transporte_value}">
            <td><span class="badge badge-id">{c["id_comuna"]}</span></td>
            <td>{c["comuna"]}</td>
            <td>{dias_display}</td>
            <td>{precio_display}</td>
            <td>{c.get("fecha_entrega", "-") or "-"}</td>
            <td>{c.get("transporte", "-") or "-"}</td>
            <td>{c.get("ciudad", "-")}</td>
            <td><span class="badge {estado_badge}">{c["estado"]}</span></td>
        </tr>\n'''
    
    # Stats classes
    no_disp_class = "red" if summary["no_disponibles"] > 0 else "green"
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="600">
    <title>PCFactory Delivery Monitor - Nacional</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
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
            --font-sans: 'Ubuntu', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1.5rem;
                border-bottom: 1px solid var(--border);
                flex-wrap: wrap;
                gap: 1rem;
            }}
        .logo {{ display: flex; align-items: center; gap: 1rem; }}
        .logo-icon {{ width: 48px; height: 48px; flex-shrink: 0; }}
        .logo-icon img {{ width: 100%; height: 100%; object-fit: contain; }}
        .logo-text h1 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.01em; }}
        .logo-text span {{ font-size: 0.875rem; color: var(--text-muted); }}
        .timestamp {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-secondary);
            background: var(--bg-card);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .nav-links {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}
        .nav-link {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.625rem 1rem;
            background: var(--bg-card);
            border-radius: 8px;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }}
        .nav-link:hover {{ background: var(--bg-hover); color: var(--text-primary); }}
        .nav-link.active {{ background: var(--accent-green); color: #000000; border-color: var(--accent-green); font-weight: 500; }}
        
        .product-panel {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .product-current {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .product-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .product-value {{
            font-family: var(--font-mono);
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        .product-value strong {{
            color: var(--text-primary);
        }}
        .product-sep {{
            color: var(--border);
            margin: 0 0.25rem;
        }}
        .change-product-btn {{
            margin-left: auto;
            background: var(--bg-hover);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .change-product-btn:hover {{
            background: var(--bg-secondary);
            color: var(--text-primary);
            border-color: var(--accent-blue);
        }}
        .product-form {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }}
        .form-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .form-group {{
            flex: 1;
        }}
        .form-group label {{
            display: block;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .form-group input {{
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.6rem 0.8rem;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 0.875rem;
        }}
        .form-group input:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        .form-actions {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .btn-primary {{
            background: var(--accent-blue);
            color: white;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s;
        }}
        .btn-primary:hover {{
            background: #2563eb;
            transform: translateY(-1px);
        }}
        .form-hint {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
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
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.2s ease;
        }}
        .stat-card:hover {{ background: var(--bg-hover); transform: translateY(-2px); }}
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stat-value {{ font-family: var(--font-mono); font-size: 1.75rem; font-weight: 700; }}
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
        
        .regions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .region-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .region-card:hover {{ background: var(--bg-hover); transform: translateY(-2px); }}
        .region-card.selected {{ border-color: var(--accent-blue); background: var(--bg-hover); }}
        .region-name {{ font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem; }}
        .region-cob {{ font-family: var(--font-mono); font-size: 1.5rem; font-weight: 700; }}
        .region-cob.green {{ color: var(--accent-green); }}
        .region-cob.yellow {{ color: var(--accent-yellow); }}
        .region-cob.red {{ color: var(--accent-red); }}
        .region-stats {{
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}
        
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
            width: 40px;
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
        .table-container {{ overflow-x: auto; max-height: 600px; overflow-y: auto; }}
        table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        th {{
            text-align: left;
            padding: 0.75rem 1rem;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            background: var(--bg-secondary);
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            cursor: pointer;
            user-select: none;
            transition: all 0.2s;
        }}
        th:nth-child(1) {{ width: 6%; }}  /* ID */
        th:nth-child(2) {{ width: 16%; }} /* Comuna */
        th:nth-child(3) {{ width: 8%; }}  /* Días */
        th:nth-child(4) {{ width: 12%; }} /* Precio */
        th:nth-child(5) {{ width: 12%; }} /* Fecha */
        th:nth-child(6) {{ width: 14%; }} /* Transporte */
        th:nth-child(7) {{ width: 16%; }} /* Ciudad */
        th:nth-child(8) {{ width: 12%; }} /* Estado */
        th:hover {{
            background: var(--bg-hover);
            color: var(--text-primary);
        }}
        th.sortable::after {{
            content: ' ⇅';
            opacity: 0.3;
            font-size: 0.8rem;
        }}
        th.sort-asc::after {{
            content: ' ↑';
            opacity: 1;
            color: var(--accent-blue);
        }}
        th.sort-desc::after {{
            content: ' ↓';
            opacity: 1;
            color: var(--accent-blue);
        }}
        td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: var(--bg-hover); }}
        .region-header-row {{
            background: var(--bg-secondary) !important;
        }}
        .region-header-row td {{
            padding: 0.5rem 1rem;
            color: var(--accent-blue);
        }}
        .badge {{
            font-family: var(--font-mono);
            font-size: 0.7rem;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        .badge-id {{ background: var(--bg-hover); color: var(--text-secondary); }}
        .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .badge-warn {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}
        .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
        .badge-muted {{ background: var(--bg-secondary); color: var(--text-muted); }}
        .product-info {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: var(--text-muted);
            background: var(--bg-secondary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .filter-input {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem 0.75rem;
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 0.875rem;
            width: 100%;
            transition: all 0.2s;
        }}
        .filter-input:hover {{
            border-color: var(--accent-blue);
        }}
        .filter-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        .filters-panel {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            align-items: end;
        }}
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .filter-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }}
        .filter-select {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem 0.75rem;
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .filter-select:hover {{
            border-color: var(--accent-blue);
        }}
        .filter-select:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        .filter-reset {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.5rem 1rem;
            color: var(--text-secondary);
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 500;
        }}
        .filter-reset:hover {{
            background: var(--bg-hover);
            color: var(--text-primary);
            border-color: var(--accent-red);
        }}
        .footer {{ text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .regions-grid {{ grid-template-columns: repeat(2, 1fr); }}
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
                    <span>Despacho Nacional - Chile</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <div class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link active">🚚 Despacho Nacional</a>
            <a href="checkout.html" class="nav-link">🛒 Checkout</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
            <a href="banners.html" class="nav-link">🎨 Banners</a>
            <a href="pagespeed.html" class="nav-link">⚡ PageSpeed</a>
        </div>
        
        <div class="product-panel">
            <div class="product-current">
                <span class="product-label">Monitoreando:</span>
                <span class="product-value">Producto <strong>{report["producto"]}</strong></span>
                <span class="product-sep">|</span>
                <span class="product-value">Total <strong>${formato_clp(report["total"])}</strong></span>
                <span class="product-sep">|</span>
                <span class="product-value">Cantidad <strong>{report["cantidad"]}</strong></span>
            </div>
            <button class="change-product-btn" onclick="toggleProductForm()">⚙️ Cambiar Producto</button>
            <div class="product-form" id="productForm" style="display: none;">
                <div class="form-row">
                    <div class="form-group">
                        <label>ID Producto</label>
                        <input type="number" id="inputProducto" value="{report["producto"]}" placeholder="Ej: 53880">
                    </div>
                    <div class="form-group">
                        <label>Total Carrito</label>
                        <input type="number" id="inputTotal" value="{report["total"]}" placeholder="Ej: 554990">
                    </div>
                </div>
                <div class="form-actions">
                    <a id="runWorkflowBtn" class="btn-primary" href="#" target="_blank">🚀 Ejecutar Monitor</a>
                    <span class="form-hint">Se abrirá GitHub Actions para confirmar</span>
                </div>
            </div>
        </div>
        
        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>
        
        <div class="health-card">
            <div class="health-score">{summary["cobertura_pct"]}%</div>
            <div class="health-label">Cobertura Nacional ({summary["disponibles"]}/{summary["total_comunas"]} comunas)</div>
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
                <div class="stat-label">Despacho Gratis</div>
                <div class="stat-value green">{summary["despacho_gratis"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Promedio Días</div>
                <div class="stat-value blue">{summary["promedio_dias"]}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Precio Promedio</div>
                <div class="stat-value yellow">${formato_clp(summary["precio_promedio"])}</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <span>🗺️</span>
                <h2>Cobertura por Región</h2>
            </div>
            <div style="padding: 1rem;">
                <div class="regions-grid">
                    {region_cards}
                </div>
            </div>
        </div>
        
        <div class="dist-container">
            <div class="dist-title">Distribución por Días de Entrega</div>
            {dias_chart if dias_chart else '<p style="color: var(--text-muted);">Sin datos</p>'}
        </div>
        
        {no_disp_section}
        
        <div class="section">
            <div class="section-header">
                <span>📍</span>
                <h2>Todas las Comunas</h2>
                <span class="section-count" id="visibleCount">{len(comunas)}</span>
            </div>

            <div class="filters-panel">
                <div class="filter-group">
                    <label class="filter-label">🔍 Buscar</label>
                    <input type="text" class="filter-input" placeholder="Buscar comuna..." id="filterInput">
                </div>
                <div class="filter-group">
                    <label class="filter-label">📊 Estado</label>
                    <select class="filter-select" id="filterEstado">
                        <option value="">Todos</option>
                        <option value="Disponible">Disponible</option>
                        <option value="No disponible">No disponible</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">📦 Días</label>
                    <select class="filter-select" id="filterDias">
                        <option value="">Todos</option>
                        <option value="1-2">1-2 días</option>
                        <option value="3-5">3-5 días</option>
                        <option value="6+">6+ días</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">💰 Precio</label>
                    <select class="filter-select" id="filterPrecio">
                        <option value="">Todos</option>
                        <option value="gratis">Gratis</option>
                        <option value="0-5000">$0 - $5.000</option>
                        <option value="5000-10000">$5.000 - $10.000</option>
                        <option value="10000+">$10.000+</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label class="filter-label">🚚 Transporte</label>
                    <select class="filter-select" id="filterTransporte">
                        <option value="">Todos</option>
                        <option value="TurBus">TurBus</option>
                        <option value="Chileexpress">Chileexpress</option>
                        <option value="Chilexpress">Chilexpress</option>
                        <option value="Starken">Starken</option>
                        <option value="Bluexpress">Bluexpress</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button class="filter-reset" onclick="resetFilters()">🔄 Limpiar Filtros</button>
                </div>
            </div>

            <div class="table-container">
                <table id="comunasTable">
                    <thead>
                        <tr>
                            <th class="sortable" data-column="id" data-type="number">ID</th>
                            <th class="sortable" data-column="comuna" data-type="string">Comuna</th>
                            <th class="sortable" data-column="dias" data-type="number">Días</th>
                            <th class="sortable" data-column="precio" data-type="number">Precio</th>
                            <th data-column="fecha">Fecha</th>
                            <th data-column="transporte">Transporte</th>
                            <th data-column="ciudad">Ciudad</th>
                            <th class="sortable" data-column="estado" data-type="string">Estado</th>
                        </tr>
                    </thead>
                    <tbody>{comunas_rows}</tbody>
                </table>
            </div>
        </div>
        
        <footer class="footer">
            <p>Actualización automática cada 10 minutos</p>
            <p>Hecho con ❤️ por Ain Cortés Catoni</p>
        </footer>
    </div>
    
    <script>
        // Estado global
        let currentSort = {{ column: null, direction: 'asc' }};
        let selectedRegion = null;

        // Aplicar todos los filtros
        function applyFilters() {{
            const searchTerm = document.getElementById('filterInput').value.toLowerCase();
            const estadoFilter = document.getElementById('filterEstado').value;
            const diasFilter = document.getElementById('filterDias').value;
            const precioFilter = document.getElementById('filterPrecio').value;
            const transporteFilter = document.getElementById('filterTransporte').value;

            const rows = document.querySelectorAll('#comunasTable tbody tr');
            let visibleCount = 0;

            rows.forEach(row => {{
                if (row.classList.contains('region-header-row')) {{
                    row.style.display = '';
                    return;
                }}

                let show = true;

                // Filtro de búsqueda
                if (searchTerm && !row.textContent.toLowerCase().includes(searchTerm)) {{
                    show = false;
                }}

                // Filtro de región
                if (selectedRegion && row.dataset.region !== selectedRegion) {{
                    show = false;
                }}

                // Filtro de estado
                if (estadoFilter && row.dataset.estado !== estadoFilter) {{
                    show = false;
                }}

                // Filtro de días
                if (diasFilter) {{
                    const dias = parseInt(row.dataset.dias);
                    if (diasFilter === '1-2' && (dias > 2 || dias === 999)) show = false;
                    if (diasFilter === '3-5' && (dias < 3 || dias > 5)) show = false;
                    if (diasFilter === '6+' && (dias < 6 || dias === 999)) show = false;
                }}

                // Filtro de precio
                if (precioFilter) {{
                    const precio = parseInt(row.dataset.precio);
                    const gratis = row.dataset.gratis === 'True';

                    if (precioFilter === 'gratis' && !gratis) show = false;
                    if (precioFilter === '0-5000' && (precio > 5000 || gratis)) show = false;
                    if (precioFilter === '5000-10000' && (precio < 5000 || precio > 10000)) show = false;
                    if (precioFilter === '10000+' && precio < 10000) show = false;
                }}

                // Filtro de transporte
                if (transporteFilter && row.dataset.transporte !== transporteFilter) {{
                    show = false;
                }}

                row.style.display = show ? '' : 'none';
                if (show) visibleCount++;
            }});

            // Actualizar contador
            document.getElementById('visibleCount').textContent = visibleCount;
        }}

        // Reiniciar filtros
        function resetFilters() {{
            document.getElementById('filterInput').value = '';
            document.getElementById('filterEstado').value = '';
            document.getElementById('filterDias').value = '';
            document.getElementById('filterPrecio').value = '';
            document.getElementById('filterTransporte').value = '';
            document.querySelectorAll('.region-card').forEach(c => c.classList.remove('selected'));
            selectedRegion = null;
            resetTableOrder();  // También resetear orden
            applyFilters();
        }}

        // Guardar orden original
        const originalOrder = Array.from(document.querySelectorAll('#comunasTable tbody tr'));

        // Ordenamiento de tabla
        function sortTable(column, type) {{
            const tbody = document.querySelector('#comunasTable tbody');
            const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => !r.classList.contains('region-header-row'));

            // Si ya está ordenado por esta columna en desc, resetear al orden original
            if (currentSort.column === column && currentSort.direction === 'desc') {{
                resetTableOrder();
                return;
            }}

            // Toggle dirección si es la misma columna
            if (currentSort.column === column) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.column = column;
                currentSort.direction = 'asc';
            }}

            // Ordenar
            rows.sort((a, b) => {{
                let aVal = a.dataset[column];
                let bVal = b.dataset[column];

                if (type === 'number') {{
                    aVal = parseFloat(aVal) || 999999;
                    bVal = parseFloat(bVal) || 999999;
                    return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
                }} else {{
                    aVal = (aVal || '').toLowerCase();
                    bVal = (bVal || '').toLowerCase();
                    if (currentSort.direction === 'asc') {{
                        return aVal.localeCompare(bVal);
                    }} else {{
                        return bVal.localeCompare(aVal);
                    }}
                }}
            }});

            // Limpiar y re-insertar filas
            tbody.innerHTML = '';
            let lastRegion = null;

            rows.forEach(row => {{
                // Re-insertar headers de región si es necesario
                const region = row.dataset.region;
                if (region !== lastRegion) {{
                    lastRegion = region;
                    const regionHeader = document.createElement('tr');
                    regionHeader.className = 'region-header-row';
                    regionHeader.innerHTML = `<td colspan="8"><strong>${{getRegionName(region)}}</strong></td>`;
                    tbody.appendChild(regionHeader);
                }}
                tbody.appendChild(row);
            }});

            // Actualizar indicadores visuales
            updateSortIndicators();
        }}

        // Resetear tabla al orden original (por región)
        function resetTableOrder() {{
            const tbody = document.querySelector('#comunasTable tbody');
            tbody.innerHTML = '';

            // Restaurar orden original
            originalOrder.forEach(row => {{
                tbody.appendChild(row.cloneNode(true));
            }});

            // Resetear estado de ordenamiento
            currentSort = {{ column: null, direction: 'asc' }};

            // Limpiar indicadores visuales
            updateSortIndicators();
        }}

        // Actualizar indicadores visuales de ordenamiento
        function updateSortIndicators() {{
            document.querySelectorAll('th.sortable').forEach(th => {{
                th.classList.remove('sort-asc', 'sort-desc');
            }});

            if (currentSort.column) {{
                const activeHeader = document.querySelector(`th[data-column="${{currentSort.column}}"]`);
                if (activeHeader) {{
                    activeHeader.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
                }}
            }}
        }}

        // Obtener nombre de región (simplificado)
        function getRegionName(regionId) {{
            const names = {{
                '1': 'Tarapacá', '2': 'Antofagasta', '3': 'Atacama', '4': 'Coquimbo',
                '5': 'Valparaíso', '6': "O'Higgins", '7': 'Maule', '8': 'Biobío',
                '9': 'Araucanía', '10': 'Los Lagos', '11': 'Aysén', '12': 'Magallanes',
                '13': 'Metropolitana', '14': 'Los Ríos', '15': 'Arica y Parinacota', '16': 'Ñuble'
            }};
            return names[regionId] || `Región ${{regionId}}`;
        }}

        // Event listeners
        document.getElementById('filterInput').addEventListener('input', applyFilters);
        document.getElementById('filterEstado').addEventListener('change', applyFilters);
        document.getElementById('filterDias').addEventListener('change', applyFilters);
        document.getElementById('filterPrecio').addEventListener('change', applyFilters);
        document.getElementById('filterTransporte').addEventListener('change', applyFilters);

        // Click en headers para ordenar
        document.querySelectorAll('th.sortable').forEach(th => {{
            th.addEventListener('click', function() {{
                const column = this.dataset.column;
                const type = this.dataset.type || 'string';
                sortTable(column, type);
            }});
        }});

        // Click en región para filtrar
        document.querySelectorAll('.region-card').forEach(card => {{
            card.addEventListener('click', function() {{
                const regionId = this.dataset.region;
                const isSelected = this.classList.contains('selected');

                // Toggle selección
                document.querySelectorAll('.region-card').forEach(c => c.classList.remove('selected'));

                if (!isSelected) {{
                    this.classList.add('selected');
                    selectedRegion = regionId;
                }} else {{
                    selectedRegion = null;
                }}

                applyFilters();
            }});
        }});

        // Toggle formulario de producto
        function toggleProductForm() {{
            const form = document.getElementById('productForm');
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
            if (form.style.display === 'block') {{
                updateWorkflowUrl();
            }}
        }}

        // Actualizar URL del workflow
        function updateWorkflowUrl() {{
            const producto = document.getElementById('inputProducto').value;
            const total = document.getElementById('inputTotal').value;
            const btn = document.getElementById('runWorkflowBtn');
            const repoUrl = 'https://github.com/aincatoni/pcfactory-monitor/actions/workflows/monitor.yml';
            btn.href = repoUrl;
            btn.title = `Producto: ${{producto}}, Total: ${{total}}`;
        }}

        // Escuchar cambios en inputs
        document.getElementById('inputProducto')?.addEventListener('input', updateWorkflowUrl);
        document.getElementById('inputTotal')?.addEventListener('input', updateWorkflowUrl);
    </script>
</body>
</html>'''
    
    return html

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="PCFactory Delivery Monitor - Nacional")
    parser.add_argument("--producto", type=int, required=True, help="ID del producto")
    parser.add_argument("--total", type=int, required=True, help="Total del carrito")
    parser.add_argument("--tienda", type=int, default=11, help="ID tienda (default: 11)")
    parser.add_argument("--cantidad", type=int, default=1, help="Cantidad (default: 1)")
    parser.add_argument("--workers", type=int, default=5, help="Workers paralelos")
    parser.add_argument("--delay-min", type=float, default=0.2)
    parser.add_argument("--delay-max", type=float, default=0.5)
    parser.add_argument("--output-dir", type=str, default="./output")
    parser.add_argument("--ciudades", type=str, default="ciudad.csv", help="CSV de ciudades")
    parser.add_argument("--comunas", type=str, default="comuna.csv", help="CSV de comunas")
    parser.add_argument("--relacion", type=str, default="ciudad_comuna.csv", help="CSV relación ciudad-comuna")
    parser.add_argument("--region", type=int, default=None, help="Filtrar por región (opcional)")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Delivery Monitor - Nacional")
    print("=" * 60)
    
    report = run_delivery_monitor(
        producto=args.producto,
        total=args.total,
        ciudades_path=args.ciudades,
        comunas_path=args.comunas,
        relacion_path=args.relacion,
        tienda_id=args.tienda,
        cantidad=args.cantidad,
        workers=args.workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        region_filter=args.region,
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
    print("RESUMEN NACIONAL")
    print("=" * 60)
    print(f"Total comunas: {summary['total_comunas']}")
    print(f"Con despacho: {summary['disponibles']}")
    print(f"Sin despacho: {summary['no_disponibles']}")
    print(f"Cobertura: {summary['cobertura_pct']}%")
    print(f"Promedio días: {summary['promedio_dias']}")
    
    print("\nCobertura por región:")
    for reg_id in sorted(report["stats_por_region"].keys()):
        stats = report["stats_por_region"][reg_id]
        print(f"  {stats['nombre']}: {stats['cobertura_pct']}% ({stats['disponibles']}/{stats['total']})")
    
    if report["no_disponibles"]:
        print(f"\nComunas sin despacho ({len(report['no_disponibles'])}):")
        for c in report["no_disponibles"][:10]:
            print(f"  - [{c['id_comuna']}] {c['comuna']} ({c['region']})")
        if len(report["no_disponibles"]) > 10:
            print(f"  ... y {len(report['no_disponibles']) - 10} más")
    
    print("\n[OK] Monitoreo completado!")

if __name__ == "__main__":
    main()
