#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Payment Methods Dashboard Generator
Genera el dashboard HTML a partir de los resultados de Playwright
"""
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any


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

def formato_clp(numero: int) -> str:
    """Formatea número al estilo chileno"""
    if numero is None:
        return "0"
    return f"{numero:,}".replace(",", ".")

# Lista de medios de pago esperados (para detectar los que faltan)
EXPECTED_PAYMENT_METHODS = [
    "Transferencia ETPay",
    "Compraquí", 
    "Mastercard Click to Pay",
    "Tarjeta de Débito (Webpay)",
    "Tarjeta de Crédito (Webpay)"
]

def load_results(results_path: str) -> Dict:
    """Carga los resultados del test de Playwright"""
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def load_history(history_path: str) -> List[Dict]:
    """Carga el historial de ejecuciones"""
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_history(history: List[Dict], history_path: str):
    """Guarda el historial (máximo 100 entradas)"""
    trimmed = history[-100:]
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(trimmed, f, ensure_ascii=False, indent=2)

def generate_html_dashboard(report: Dict, history: List[Dict]) -> str:
    """Genera el dashboard HTML"""
    
    # Timestamp - usar hora Chile
    timestamp = report.get("timestamp", datetime.now(timezone.utc).isoformat())
    timestamp_display = format_chile_timestamp(timestamp)
    
    # Summary
    summary = report.get("summary", {"total": 0, "passed": 0, "failed": 0})
    results = report.get("results", [])
    
    # Calcular métodos reportados vs esperados
    reported_methods = set(r.get("paymentMethod", "") for r in results)
    missing_count = len([m for m in EXPECTED_PAYMENT_METHODS if m not in reported_methods])
    
    total = len(EXPECTED_PAYMENT_METHODS)  # Usar total esperado
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0) + missing_count  # Incluir faltantes como problemas
    
    # Status
    if failed == 0 and passed == total:
        status_class = "healthy"
        status_text = "Todos los medios de pago operativos"
        status_color = "#10b981"
    elif missing_count > 0 and summary.get("failed", 0) == 0:
        status_class = "warning"
        status_text = f"{missing_count} medio(s) sin verificar"
        status_color = "#f59e0b"
    elif failed > 0:
        status_class = "critical"
        status_text = f"{failed} medio(s) de pago con problemas"
        status_color = "#ef4444"
    else:
        status_class = "warning"
        status_text = "Sin datos de monitoreo"
        status_color = "#f59e0b"
    
    # Porcentaje de disponibilidad (solo de los verificados)
    verified_total = summary.get("total", 0)
    availability = round((passed / verified_total * 100) if verified_total > 0 else 0, 1)
    
    # Calcular uptime 24h
    uptime_stats = {}
    last_24h = [h for h in history if _is_within_24h(h.get("timestamp", ""))]
    for entry in last_24h:
        for r in entry.get("results", []):
            method = r.get("paymentMethod", "")
            if method not in uptime_stats:
                uptime_stats[method] = {"total": 0, "passed": 0}
            uptime_stats[method]["total"] += 1
            if r.get("status") == "PASSED":
                uptime_stats[method]["passed"] += 1
    
    # Generar tarjetas de medios de pago
    payment_cards = ""
    reported_methods = set()
    
    # Primero, mostrar los que están en el reporte
    for r in results:
        method_name = r.get("paymentMethod", "Desconocido")
        reported_methods.add(method_name)
        status = r.get("status", "UNKNOWN")
        duration = r.get("duration", 0)
        error = r.get("error", "")
        gateway_url = r.get("gatewayUrl", "")
        video_path = r.get("videoPath", "")  # Ruta del video
        
        card_class = "status-ok" if status == "PASSED" else "status-error"
        status_icon = "✅" if status == "PASSED" else "❌"
        status_badge = "Operativo" if status == "PASSED" else "Con problemas"
        
        # Uptime 24h
        uptime = uptime_stats.get(method_name, {"total": 0, "passed": 0})
        uptime_pct = round((uptime["passed"] / uptime["total"] * 100) if uptime["total"] > 0 else 100, 1)
        
        gateway_info = ""
        if gateway_url:
            try:
                from urllib.parse import urlparse
                host = urlparse(gateway_url).netloc
                gateway_info = f'<div class="gateway-url">Gateway: {host}</div>'
            except:
                gateway_info = f'<div class="gateway-url">Gateway alcanzado</div>'
        
        error_info = f'<div class="error-message">{error}</div>' if error else ""
        
        # Botón de video si existe
        video_button = ""
        if video_path:
            video_button = f'''
                <button class="video-btn" onclick="openVideoModal('{video_path}', '{method_name}')">
                    <span class="video-icon">🎬</span> Ver video
                </button>
            '''
        
        payment_cards += f'''
        <div class="payment-card {card_class}">
            <div class="payment-header">
                <span class="status-icon">{status_icon}</span>
                <h3>{method_name}</h3>
            </div>
            <div class="payment-body">
                <div class="status-badge {card_class}">{status_badge}</div>
                <div class="payment-stats">
                    <div class="stat">
                        <span class="stat-label">Uptime 24h</span>
                        <span class="stat-value">{uptime_pct}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Duración</span>
                        <span class="stat-value">{duration / 1000:.1f}s</span>
                    </div>
                </div>
                {error_info}
                {gateway_info}
                {video_button}
            </div>
        </div>
        '''
    
    # Luego, agregar los medios esperados que no aparecen en el reporte
    missing_methods = [m for m in EXPECTED_PAYMENT_METHODS if m not in reported_methods]
    for method_name in missing_methods:
        # Buscar en historial si hay datos previos
        uptime = uptime_stats.get(method_name, {"total": 0, "passed": 0})
        uptime_pct = round((uptime["passed"] / uptime["total"] * 100) if uptime["total"] > 0 else 0, 1)
        
        payment_cards += f'''
        <div class="payment-card status-missing">
            <div class="payment-header">
                <span class="status-icon">⚠️</span>
                <h3>{method_name}</h3>
            </div>
            <div class="payment-body">
                <div class="status-badge status-missing">Sin datos</div>
                <div class="payment-stats">
                    <div class="stat">
                        <span class="stat-label">Uptime 24h</span>
                        <span class="stat-value">{uptime_pct}%</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Duración</span>
                        <span class="stat-value">--</span>
                    </div>
                </div>
                <div class="error-message">No se ejecutó el test en esta verificación</div>
            </div>
        </div>
        '''
    
    # Generar historial
    history_rows = ""
    for entry in reversed(history[-48:]):
        try:
            dt = datetime.fromisoformat(entry.get("timestamp", "").replace('Z', '+00:00'))
            dt_chile = utc_to_chile(dt)
            time_str = dt_chile.strftime("%d/%m %H:%M")
        except:
            time_str = entry.get("timestamp", "")[:16]
        
        statuses = ""
        for r in entry.get("results", []):
            icon = "✅" if r.get("status") == "PASSED" else "❌"
            statuses += f'<span title="{r.get("paymentMethod", "")}">{icon}</span> '
        
        entry_summary = entry.get("summary", {})
        history_rows += f'''
        <tr>
            <td>{time_str}</td>
            <td class="status-icons">{statuses}</td>
            <td>{entry_summary.get("passed", 0)}/{entry_summary.get("total", 0)}</td>
        </tr>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <title>PCFactory - Monitor de Medios de Pago</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>💳</text></svg>">
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
            --font-mono: 'JetBrains Mono', ui-monospace, monospace;
            --font-sans: 'Ubuntu', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding-bottom: 2rem;
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
            justify-content: flex-start;
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
        .status-banner.healthy {{ border-color: var(--accent-green); background: rgba(16, 185, 129, 0.1); }}
        .status-banner.critical {{ border-color: var(--accent-red); background: rgba(239, 68, 68, 0.1); }}
        .status-banner.warning {{ border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.1); }}
        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        .status-banner.healthy .status-indicator {{ background: var(--accent-green); }}
        .status-banner.critical .status-indicator {{ background: var(--accent-red); }}
        .status-banner.warning .status-indicator {{ background: var(--accent-yellow); }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .status-text {{ font-size: 1.125rem; font-weight: 600; }}
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
            text-align: center;
            transition: all 0.2s ease;
        }}
        .stat-card:hover {{ background: var(--bg-hover); transform: translateY(-2px); }}
        .stat-value {{
            font-family: var(--font-mono);
            font-size: 2.5rem;
            font-weight: 700;
        }}
        .stat-value.green {{ color: var(--accent-green); }}
        .stat-value.red {{ color: var(--accent-red); }}
        .stat-value.blue {{ color: var(--accent-blue); }}
        .stat-value.yellow {{ color: var(--accent-yellow); }}
        .stat-label {{ color: var(--text-muted); font-size: 0.875rem; margin-top: 0.5rem; }}
        .section-title {{
            font-size: 1.25rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        .payments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .payment-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .payment-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        .payment-card.status-ok {{ border-left: 4px solid var(--accent-green); }}
        .payment-card.status-error {{ border-left: 4px solid var(--accent-red); }}
        .payment-card.status-missing {{ border-left: 4px solid var(--accent-yellow); opacity: 0.8; }}
        .payment-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.25rem;
            background: var(--bg-secondary);
        }}
        .status-icon {{ font-size: 1.5rem; }}
        .payment-header h3 {{ font-size: 1rem; font-weight: 500; }}
        .payment-body {{ padding: 1.25rem; }}
        .status-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            margin-bottom: 1rem;
        }}
        .status-badge.status-ok {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }}
        .status-badge.status-error {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }}
        .status-badge.status-missing {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-yellow); }}
        .payment-stats {{ display: flex; gap: 1.5rem; }}
        .payment-stats .stat {{ display: flex; flex-direction: column; }}
        .payment-stats .stat-label {{ font-size: 0.75rem; color: var(--text-muted); }}
        .payment-stats .stat-value {{ font-size: 1.1rem; font-weight: 600; }}
        .error-message {{
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--accent-red);
        }}
        .status-missing .error-message {{
            background: rgba(245, 158, 11, 0.1);
            color: var(--accent-yellow);
        }}
        .gateway-url {{
            margin-top: 0.75rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        .video-btn {{
            margin-top: 1rem;
            width: 100%;
            padding: 0.6rem 1rem;
            background: linear-gradient(135deg, var(--accent-blue), #6366f1);
            border: none;
            border-radius: 8px;
            color: white;
            font-family: var(--font-sans);
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .video-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }}
        .video-icon {{ font-size: 1rem; }}
        
        /* Modal de video */
        .video-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .video-modal.active {{ display: flex; }}
        .video-modal-content {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            max-width: 90%;
            max-height: 90%;
            position: relative;
        }}
        .video-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .video-modal-header h3 {{ font-size: 1.1rem; }}
        .video-modal-close {{
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.25rem;
            line-height: 1;
        }}
        .video-modal-close:hover {{ color: var(--text-primary); }}
        .video-modal video {{
            max-width: 100%;
            max-height: 70vh;
            border-radius: 8px;
        }}
        .history-section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .history-table-container {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin: 0 -1.5rem;
            padding: 0 1.5rem;
        }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 500px;
        }}
        .history-table th, .history-table td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
        }}
        .history-table th {{
            color: var(--text-muted);
            font-weight: 500;
            font-size: 0.8rem;
            text-transform: uppercase;
        }}
        .history-table td:first-child {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
        }}
        .status-icons {{ display: flex; gap: 0.25rem; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header {{ flex-direction: column; text-align: center; }}
            .payments-grid {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stat-value {{ font-size: 1.75rem; }}
            .history-section {{ padding: 1rem; }}
            .history-table-container {{
                margin: 0 -1rem;
                padding: 0 1rem;
            }}
            .history-table th,
            .history-table td {{
                padding: 0.5rem 0.75rem;
                font-size: 0.75rem;
            }}
            .section-title {{
                font-size: 1.1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="logo">
                <div class="logo-icon">
                    <img src="https://assets-v3.pcfactory.cl/uploads/e964d6b9-e816-439f-8b97-ad2149772b7b/original/pcfactory-isotipo.svg" alt="PCFactory">
                </div>
                <div class="logo-text">
                    <h1>pc Factory Monitor</h1>
                    <span>Medios de Pago</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <nav class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link active">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
            <a href="banners.html" class="nav-link">🎨 Banners</a>
        </nav>
        
        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value blue">{total}</div>
                <div class="stat-label">Total Medios</div>
            </div>
            <div class="stat-card">
                <div class="stat-value green">{passed}</div>
                <div class="stat-label">Operativos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {"red" if summary.get("failed", 0) > 0 else ("yellow" if missing_count > 0 else "")}">{failed}</div>
                <div class="stat-label">Con Problemas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {"green" if availability >= 80 else "red"}">{availability}%</div>
                <div class="stat-label">Disponibilidad</div>
            </div>
        </div>
        
        <h2 class="section-title">Estado de Medios de Pago</h2>
        <div class="payments-grid">
            {payment_cards if payment_cards else '<p style="color: var(--text-muted);">No hay datos disponibles</p>'}
        </div>
        
        <div class="history-section">
            <h2 class="section-title" style="border-bottom: none; margin-bottom: 1rem;">Historial de Verificaciones</h2>
            <div class="history-table-container">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Fecha/Hora</th>
                            <th>Estado</th>
                            <th>Resultado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history_rows if history_rows else '<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">Sin historial</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        
        <footer class="footer">
            <p>Actualización automática: 9am, 2pm, 8pm Chile</p>
            <p>Hecho con ❤️ por Ain Cortés Catoni</p>
        </footer>
    </div>
    
    <!-- Modal de video -->
    <div id="videoModal" class="video-modal">
        <div class="video-modal-content">
            <div class="video-modal-header">
                <h3 id="videoModalTitle">Video del test</h3>
                <button class="video-modal-close" onclick="closeVideoModal()">&times;</button>
            </div>
            <video id="videoPlayer" controls>
                <source src="" type="video/webm">
                Tu navegador no soporta video HTML5.
            </video>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(() => location.reload(), 5 * 60 * 1000);
        
        // Funciones del modal de video
        function openVideoModal(videoPath, methodName) {{
            const modal = document.getElementById('videoModal');
            const video = document.getElementById('videoPlayer');
            const title = document.getElementById('videoModalTitle');
            
            title.textContent = 'Test: ' + methodName;
            video.querySelector('source').src = videoPath;
            video.load();
            modal.classList.add('active');
            
            // Cerrar con Escape
            document.addEventListener('keydown', handleEscape);
        }}
        
        function closeVideoModal() {{
            const modal = document.getElementById('videoModal');
            const video = document.getElementById('videoPlayer');
            
            video.pause();
            modal.classList.remove('active');
            document.removeEventListener('keydown', handleEscape);
        }}
        
        function handleEscape(e) {{
            if (e.key === 'Escape') closeVideoModal();
        }}
        
        // Cerrar modal al hacer clic fuera
        document.getElementById('videoModal').addEventListener('click', function(e) {{
            if (e.target === this) closeVideoModal();
        }});
    </script>
</body>
</html>'''
    
    return html

def _is_within_24h(timestamp: str) -> bool:
    """Verifica si el timestamp está dentro de las últimas 24 horas"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        diff = datetime.now(timezone.utc) - dt
        return diff.total_seconds() < 24 * 60 * 60
    except:
        return False

def main():
    parser = argparse.ArgumentParser(description="PCFactory Payment Dashboard Generator")
    parser.add_argument("--results", type=str, default="./test-results/payment-monitor-report.json",
                       help="Ruta al archivo de resultados")
    parser.add_argument("--output-dir", type=str, default="./output",
                       help="Directorio de salida")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Payment Dashboard Generator")
    print("=" * 60)
    
    # Cargar resultados
    results = load_results(args.results)
    if not results:
        print(f"[!] No se encontró archivo de resultados: {args.results}")
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "summary": {"total": 0, "passed": 0, "failed": 0}
        }
    
    # Cargar y actualizar historial
    history_path = output_dir / "payment_history.json"
    history = load_history(str(history_path))
    
    if results.get("results"):
        current_timestamp = results.get("timestamp")
        # Verificar si ya existe una entrada en el mismo minuto para evitar duplicados
        try:
            current_dt = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            current_minute = current_dt.replace(second=0, microsecond=0).isoformat()
            existing = False
            for entry in history:
                try:
                    entry_dt = datetime.fromisoformat(entry.get("timestamp", "").replace('Z', '+00:00'))
                    entry_minute = entry_dt.replace(second=0, microsecond=0).isoformat()
                    if entry_minute == current_minute:
                        existing = True
                        break
                except:
                    continue
        except:
            # Si falla el parsing, usar comparación exacta como fallback
            existing = any(entry.get("timestamp") == current_timestamp for entry in history)

        if not existing:
            history.append({
                "timestamp": current_timestamp,
                "results": results.get("results"),
                "summary": results.get("summary")
            })
            save_history(history, str(history_path))
    
    # Generar HTML
    html_content = generate_html_dashboard(results, history)
    html_path = output_dir / "payments.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Dashboard guardado: {html_path}")
    
    # Guardar JSON
    json_path = output_dir / "payment_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[+] JSON guardado: {json_path}")
    
    # Resumen
    summary = results.get("summary", {})
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total medios: {summary.get('total', 0)}")
    print(f"Operativos: {summary.get('passed', 0)}")
    print(f"Con problemas: {summary.get('failed', 0)}")
    
    for r in results.get("results", []):
        icon = "✅" if r.get("status") == "PASSED" else "❌"
        print(f"  {icon} {r.get('paymentMethod', 'Desconocido')}")
    
    print("\n[OK] Dashboard generado!")

if __name__ == "__main__":
    main()
