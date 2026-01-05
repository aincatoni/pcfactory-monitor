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
import pandas as pd
import concurrent.futures as cf
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

DELIVERY_API = "https://www.pcfactory.cl/public-api/delivery-date"
DEFAULT_TIENDA = 11
DEFAULT_CANTIDAD = 1

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

REGIONES = {
    1: "I - Tarapacá",
    2: "II - Antofagasta", 
    3: "III - Atacama",
    4: "IV - Coquimbo",
    5: "V - Valparaíso",
    6: "VI - O'Higgins",
    7: "VII - Maule",
    8: "VIII - Biobío",
    9: "IX - La Araucanía",
    10: "X - Los Lagos",
    11: "XI - Aysén",
    12: "XII - Magallanes",
    13: "RM - Metropolitana",
    14: "XIV - Los Ríos",
    15: "XV - Arica y Parinacota",
    16: "XVI - Ñuble"
}

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE FECHA/HORA CHILE
# ═══════════════════════════════════════════════════════════════════════════════

def utc_to_chile(dt_utc):
    """Convierte datetime UTC a hora Chile (UTC-3 verano, UTC-4 invierno)."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    chile_offset = timedelta(hours=-3)
    chile_tz = timezone(chile_offset)
    return dt_utc.astimezone(chile_tz)

def get_chile_timestamp():
    """Retorna timestamp actual en hora Chile."""
    now_utc = datetime.now(timezone.utc)
    now_chile = utc_to_chile(now_utc)
    return now_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'

def formato_clp(numero):
    """Formatea número al estilo chileno con punto de miles."""
    if numero is None:
        return "$0"
    return f"${numero:,}".replace(",", ".")

# ═══════════════════════════════════════════════════════════════════════════════
# SESIÓN HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    return session

# ═══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

def load_data(ciudades_path: str, comunas_path: str, relacion_path: str):
    """Carga los CSVs y construye la estructura de datos."""
    ciudades = pd.read_csv(ciudades_path)
    comunas = pd.read_csv(comunas_path)
    relacion = pd.read_csv(relacion_path)
    
    # Crear lookup: id_comuna -> id_ciudad
    comuna_to_ciudad = dict(zip(relacion['id_comuna'], relacion['id_ciudad']))
    
    # Crear lookup: id_ciudad -> nombre_ciudad
    ciudad_nombres = dict(zip(ciudades['id_ciudad'], ciudades['ciudad']))
    
    # Construir lista de comunas para verificar
    comunas_list = []
    for _, row in comunas.iterrows():
        id_comuna = row['id_comuna']
        id_ciudad = comuna_to_ciudad.get(id_comuna)
        
        comunas_list.append({
            'id_comuna': id_comuna,
            'comuna': row['comuna'],
            'id_region': row['id_region'],
            'id_ciudad': id_ciudad,
            'ciudad': ciudad_nombres.get(id_ciudad, 'Sin ciudad')
        })
    
    return comunas_list

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE DESPACHO
# ═══════════════════════════════════════════════════════════════════════════════

def check_delivery(
    session: requests.Session,
    comuna: Dict,
    producto: int,
    total: int,
    tienda_id: int,
    cantidad: int,
    delay: float
) -> Dict:
    """Verifica disponibilidad de despacho para una comuna."""
    time.sleep(delay)
    
    result = {
        'id_comuna': comuna['id_comuna'],
        'comuna': comuna['comuna'],
        'id_region': comuna['id_region'],
        'id_ciudad': comuna['id_ciudad'],
        'ciudad': comuna['ciudad'],
        'disponible': False,
        'dias_entrega': None,
        'fecha_entrega': None,
        'transporte': None,
        'precio': None,
        'precio_normal': None,
        'gratis': False,
        'error': None,
        'estado': 'Sin despacho'
    }
    
    if comuna['id_ciudad'] is None:
        result['error'] = 'Sin ciudad asignada'
        return result
    
    payload = {
        "productos": [{
            "id_producto": producto,
            "cantidad": cantidad,
            "id_bodega": tienda_id
        }],
        "id_ciudad": int(comuna['id_ciudad']),
        "id_comuna": int(comuna['id_comuna']),
        "total": total
    }
    
    try:
        resp = session.post(DELIVERY_API, json=payload, timeout=15)
        if resp.ok:
            data = resp.json()
            if data.get("codigo") == "0":
                tarifas = data.get("resultado", {}).get("tarifas", [])
                if tarifas:
                    tarifa = tarifas[0]
                    result['disponible'] = True
                    result['dias_entrega'] = tarifa.get('dias_entrega')
                    result['fecha_entrega'] = tarifa.get('fecha_entrega')
                    result['transporte'] = tarifa.get('transporte')
                    result['precio'] = tarifa.get('precio')
                    result['precio_normal'] = tarifa.get('precio_normal')
                    result['gratis'] = tarifa.get('gratis', False)
                    result['estado'] = 'Disponible'
        else:
            result['error'] = f'HTTP {resp.status_code}'
    except Exception as e:
        result['error'] = str(e)
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# MONITOREO PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_delivery_monitor(
    producto: int,
    total: int,
    comunas_list: List[Dict],
    tienda_id: int = DEFAULT_TIENDA,
    cantidad: int = DEFAULT_CANTIDAD,
    workers: int = 5,
    delay_min: float = 0.3,
    delay_max: float = 0.7
) -> Dict:
    """Ejecuta el monitoreo de delivery para todas las comunas."""
    session = create_session()
    results = []
    
    print(f"[*] Verificando despacho para {len(comunas_list)} comunas...")
    
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for comuna in comunas_list:
            delay = random.uniform(delay_min, delay_max)
            fut = executor.submit(
                check_delivery, session, comuna, producto, total, tienda_id, cantidad, delay
            )
            futures[fut] = comuna
        
        done = 0
        for fut in cf.as_completed(futures):
            done += 1
            if done % 50 == 0 or done == len(comunas_list):
                print(f"    {done}/{len(comunas_list)} verificadas...")
            try:
                results.append(fut.result())
            except Exception as e:
                comuna = futures[fut]
                results.append({
                    'id_comuna': comuna['id_comuna'],
                    'comuna': comuna['comuna'],
                    'id_region': comuna['id_region'],
                    'disponible': False,
                    'error': str(e),
                    'estado': 'Error'
                })
    
    # Ordenar por región y comuna
    results.sort(key=lambda x: (x.get('id_region', 0), x.get('comuna', '')))
    
    # Calcular estadísticas
    disponibles = [r for r in results if r['disponible']]
    no_disponibles = [r for r in results if not r['disponible']]
    
    # Estadísticas de precio
    precios = [r['precio'] for r in disponibles if r['precio'] is not None and r['precio'] > 0]
    gratis_count = len([r for r in disponibles if r['gratis']])
    
    # Estadísticas por región
    regiones_stats = {}
    for r in results:
        region = r.get('id_region', 0)
        if region not in regiones_stats:
            regiones_stats[region] = {'total': 0, 'disponibles': 0}
        regiones_stats[region]['total'] += 1
        if r['disponible']:
            regiones_stats[region]['disponibles'] += 1
    
    # Promedio de días
    dias_list = [r['dias_entrega'] for r in disponibles if r['dias_entrega'] is not None]
    
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'producto': producto,
        'total': total,
        'summary': {
            'total_comunas': len(results),
            'disponibles': len(disponibles),
            'no_disponibles': len(no_disponibles),
            'cobertura_pct': round(len(disponibles) / len(results) * 100, 1) if results else 0,
            'promedio_dias': round(sum(dias_list) / len(dias_list), 1) if dias_list else 0,
            'despacho_gratis': gratis_count,
            'precio_promedio': round(sum(precios) / len(precios)) if precios else 0,
            'precio_min': min(precios) if precios else 0,
            'precio_max': max(precios) if precios else 0
        },
        'regiones': regiones_stats,
        'disponibles': disponibles,
        'no_disponibles': no_disponibles,
        'all_results': results
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html_dashboard(report: Dict) -> str:
    """Genera el dashboard HTML."""
    summary = report['summary']
    regiones_stats = report.get('regiones', {})
    all_results = report.get('all_results', [])
    producto = report.get('producto', 0)
    total = report.get('total', 0)
    timestamp = report.get('timestamp', '')
    
    # Convertir timestamp a hora Chile
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        dt_chile = utc_to_chile(dt)
        timestamp_display = dt_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'
    except:
        timestamp_display = timestamp
    
    # Determinar estado general
    cobertura = summary['cobertura_pct']
    if cobertura >= 95:
        status_class = "healthy"
        status_text = "Todo OK" if summary['no_disponibles'] == 0 else f"{summary['no_disponibles']} comunas sin despacho"
        status_color = "#10b981"
    elif cobertura >= 80:
        status_class = "warning"
        status_text = f"{summary['no_disponibles']} comunas sin despacho"
        status_color = "#f59e0b"
    else:
        status_class = "critical"
        status_text = f"Cobertura baja: {cobertura}%"
        status_color = "#ef4444"
    
    # Cards de regiones
    region_cards = ""
    for region_id in sorted(regiones_stats.keys()):
        stats = regiones_stats[region_id]
        region_name = REGIONES.get(region_id, f"Región {region_id}")
        pct = round(stats['disponibles'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0
        
        if pct >= 95:
            card_color = "var(--accent-green)"
        elif pct >= 80:
            card_color = "var(--accent-yellow)"
        else:
            card_color = "var(--accent-red)"
        
        region_cards += f'''
        <div class="region-card" data-region="{region_id}" onclick="filterByRegion({region_id})">
            <div class="region-name">{region_name}</div>
            <div class="region-pct" style="color: {card_color}">{pct}%</div>
            <div class="region-detail">{stats['disponibles']}/{stats['total']}</div>
        </div>'''
    
    # Tabla de comunas
    comunas_rows = ""
    for c in all_results:
        dias = c.get('dias_entrega')
        precio = c.get('precio')
        gratis = c.get('gratis', False)
        
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
        
        # Precio
        if gratis:
            precio_display = '<span class="badge badge-ok">GRATIS</span>'
        elif precio is not None and precio > 0:
            precio_display = formato_clp(precio)
        else:
            precio_display = '-'
        
        estado_badge = "badge-ok" if c.get('disponible') else "badge-error"
        estado_text = "Disponible" if c.get('disponible') else "Sin despacho"
        
        comunas_rows += f'''<tr data-region="{c.get('id_region', 0)}">
            <td><span class="badge badge-id">{c['id_comuna']}</span></td>
            <td>{c['comuna']}</td>
            <td>{dias_display}</td>
            <td>{precio_display}</td>
            <td>{c.get('transporte', '-') or '-'}</td>
            <td><span class="badge {estado_badge}">{estado_text}</span></td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="600">
    <title>PCFactory Delivery Monitor - Chile</title>
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
        .product-info {{
            background: var(--bg-card);
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
            border: 1px solid var(--border);
            font-size: 0.875rem;
        }}
        .product-info span {{ color: var(--text-secondary); }}
        .product-info strong {{ color: var(--text-primary); }}
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
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
            font-size: 1.75rem;
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
        .regions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.75rem;
            margin-bottom: 2rem;
        }}
        .region-card {{
            background: var(--bg-card);
            border-radius: 10px;
            padding: 1rem;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }}
        .region-card:hover {{ background: var(--bg-hover); border-color: var(--accent-blue); }}
        .region-card.active {{ border-color: var(--accent-blue); background: rgba(59, 130, 246, 0.1); }}
        .region-name {{ font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem; }}
        .region-pct {{ font-family: var(--font-mono); font-size: 1.25rem; font-weight: 600; }}
        .region-detail {{ font-size: 0.7rem; color: var(--text-muted); }}
        .search-box {{
            margin-bottom: 1rem;
            position: relative;
        }}
        .search-box input {{
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 0.875rem;
        }}
        .search-box input:focus {{ outline: none; border-color: var(--accent-blue); }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .data-table th, .data-table td {{
            padding: 0.875rem 1rem;
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
        .data-table tr.hidden {{ display: none; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: var(--font-mono);
        }}
        .badge-id {{ background: var(--bg-secondary); color: var(--text-secondary); }}
        .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .badge-warn {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}
        .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
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
            .regions-grid {{ grid-template-columns: repeat(2, 1fr); }}
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
                    <span>Despacho Nacional - Chile</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <nav class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorias</a>
            <a href="delivery.html" class="nav-link active">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
        </nav>
        
        <div class="product-info">
            <span>Monitoreando: <strong>Producto {producto}</strong></span>
            <span>Total: <strong>{formato_clp(total)}</strong></span>
            <span>Cantidad: <strong>1</strong></span>
            <button onclick="location.href='https://github.com/aincatoni/pcfactory-monitor/actions'" style="margin-left:auto;background:var(--bg-hover);border:1px solid var(--border);color:var(--text-secondary);padding:0.5rem 1rem;border-radius:6px;cursor:pointer;font-size:0.75rem;">⚙️ Cambiar Producto</button>
        </div>
        
        <div class="status-banner {status_class}">
            <span class="status-dot"></span>
            {status_text}
        </div>
        
        <div class="hero-score">
            <div class="score-value">{summary['cobertura_pct']}%</div>
            <div class="score-label">Cobertura Nacional ({summary['disponibles']}/{summary['total_comunas']} comunas)</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">TOTAL COMUNAS</div>
                <div class="stat-value">{summary['total_comunas']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">DISPONIBLES</div>
                <div class="stat-value">{summary['disponibles']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">SIN DESPACHO</div>
                <div class="stat-value {"error" if summary['no_disponibles'] > 0 else ""}">{summary['no_disponibles']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">DESPACHO GRATIS</div>
                <div class="stat-value">{summary['despacho_gratis']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">PROMEDIO DIAS</div>
                <div class="stat-value">⏱️ {summary['promedio_dias']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">PRECIO PROMEDIO</div>
                <div class="stat-value" style="font-size:1.25rem">{formato_clp(summary['precio_promedio'])}</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📍 Cobertura por Región <span style="font-weight:normal;font-size:0.875rem;color:var(--text-muted)">(click para filtrar)</span></h2>
            <div class="regions-grid">
                {region_cards}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 Detalle por Comuna</h2>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Buscar comuna..." onkeyup="filterTable()">
            </div>
            <div style="overflow-x:auto;">
                <table class="data-table" id="comunasTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Comuna</th>
                            <th>Días</th>
                            <th>Precio</th>
                            <th>Transporte</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {comunas_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <footer class="footer">
            <p>Actualización automática 3 veces al día - Powered by GitHub Actions</p>
        </footer>
    </div>
    
    <script>
        let activeRegion = null;
        
        function filterByRegion(regionId) {{
            const cards = document.querySelectorAll('.region-card');
            const rows = document.querySelectorAll('#comunasTable tbody tr');
            
            if (activeRegion === regionId) {{
                // Deseleccionar
                activeRegion = null;
                cards.forEach(c => c.classList.remove('active'));
                rows.forEach(r => r.classList.remove('hidden'));
            }} else {{
                // Seleccionar región
                activeRegion = regionId;
                cards.forEach(c => {{
                    if (parseInt(c.dataset.region) === regionId) {{
                        c.classList.add('active');
                    }} else {{
                        c.classList.remove('active');
                    }}
                }});
                rows.forEach(r => {{
                    if (parseInt(r.dataset.region) === regionId) {{
                        r.classList.remove('hidden');
                    }} else {{
                        r.classList.add('hidden');
                    }}
                }});
            }}
        }}
        
        function filterTable() {{
            const input = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#comunasTable tbody tr');
            
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                if (text.includes(input)) {{
                    if (activeRegion === null || parseInt(row.dataset.region) === activeRegion) {{
                        row.classList.remove('hidden');
                    }}
                }} else {{
                    row.classList.add('hidden');
                }}
            }});
        }}
    </script>
</body>
</html>'''
    
    return html

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="PCFactory Delivery Monitor - Nacional")
    parser.add_argument("--producto", type=int, required=True, help="ID del producto")
    parser.add_argument("--total", type=int, required=True, help="Total del carrito")
    parser.add_argument("--ciudades", type=str, required=True, help="Ruta CSV ciudades")
    parser.add_argument("--comunas", type=str, required=True, help="Ruta CSV comunas")
    parser.add_argument("--relacion", type=str, required=True, help="Ruta CSV ciudad_comuna")
    parser.add_argument("--tienda", type=int, default=11, help="ID tienda (default: 11)")
    parser.add_argument("--cantidad", type=int, default=1, help="Cantidad (default: 1)")
    parser.add_argument("--workers", type=int, default=5, help="Workers paralelos")
    parser.add_argument("--delay-min", type=float, default=0.3)
    parser.add_argument("--delay-max", type=float, default=0.7)
    parser.add_argument("--output-dir", type=str, default="./output")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Delivery Monitor - Nacional")
    print("=" * 60)
    
    # Cargar datos
    print("[*] Cargando datos de comunas...")
    comunas_list = load_data(args.ciudades, args.comunas, args.relacion)
    print(f"[+] {len(comunas_list)} comunas cargadas")
    
    # Ejecutar monitoreo
    report = run_delivery_monitor(
        producto=args.producto,
        total=args.total,
        comunas_list=comunas_list,
        tienda_id=args.tienda,
        cantidad=args.cantidad,
        workers=args.workers,
        delay_min=args.delay_min,
        delay_max=args.delay_max
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
    summary = report['summary']
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total comunas: {summary['total_comunas']}")
    print(f"Con despacho: {summary['disponibles']}")
    print(f"Sin despacho: {summary['no_disponibles']}")
    print(f"Cobertura: {summary['cobertura_pct']}%")
    print(f"Despacho gratis: {summary['despacho_gratis']}")
    print(f"Precio promedio: {formato_clp(summary['precio_promedio'])}")
    
    if report['no_disponibles']:
        print("\nComunas sin despacho:")
        for c in report['no_disponibles'][:10]:
            print(f"  - [{c['id_comuna']}] {c['comuna']}")
        if len(report['no_disponibles']) > 10:
            print(f"  ... y {len(report['no_disponibles']) - 10} más")
    
    print("\n[OK] Monitoreo completado!")

if __name__ == "__main__":
    main()
