#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory Login Monitor Dashboard Generator
Genera el dashboard HTML a partir de los resultados de Playwright
"""
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List

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

def format_chile_timestamp(iso_timestamp):
    """Formatea un timestamp ISO a formato Chile."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        dt_chile = utc_to_chile(dt)
        return dt_chile.strftime('%d/%m/%Y %H:%M:%S') + ' Chile'
    except:
        return iso_timestamp[:19] if iso_timestamp else 'N/A'

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CARGA
# ═══════════════════════════════════════════════════════════════════════════════

def load_results(results_path):
    """Carga los resultados del test de login."""
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def load_history(history_path):
    """Carga el historial de ejecuciones."""
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'runs': []}

def save_history(history, history_path):
    """Guarda el historial."""
    history['runs'] = history['runs'][-100:]
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_status_icon(status):
    icons = {'ok': '✅', 'passed': '✅', 'error': '❌', 'failed': '❌', 'warning': '⚠️', 'pending': '⏳'}
    return icons.get(status, '❓')

def format_duration(ms):
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}min"

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html(results, history):
    """Genera el HTML del dashboard."""
    timestamp = results.get('timestamp', datetime.now().isoformat())
    timestamp_display = format_chile_timestamp(timestamp)
    
    tests = results.get('tests', [])
    summary = results.get('summary', {})
    overall_status = results.get('overallStatus', 'pending')
    
    # Calcular uptime 24h
    recent_runs = []
    now = datetime.now(timezone.utc)
    for r in history.get('runs', []):
        try:
            run_time = datetime.fromisoformat(r.get('timestamp', '2000-01-01').replace('Z', '+00:00'))
            if (now - run_time).total_seconds() < 86400:
                recent_runs.append(r)
        except:
            pass
    
    if recent_runs:
        ok_runs = len([r for r in recent_runs if r.get('status') in ['ok', 'passed']])
        uptime_24h = round((ok_runs / len(recent_runs)) * 100)
    else:
        uptime_24h = 100 if overall_status in ['ok', 'passed'] else 0
    
    # Estadísticas
    passed = summary.get('passed', 0)
    total = summary.get('total', 0)
    failed = summary.get('failed', 0)
    health_score = summary.get('successRate', 100 if failed == 0 and total > 0 else 0)
    
    # Determinar estado
    if overall_status in ['ok', 'passed'] or (total > 0 and failed == 0):
        status_class = 'healthy'
        status_text = 'Login Operativo'
        status_color = '#10b981'
    elif total == 0:
        status_class = 'warning'
        status_text = 'Sin datos de monitoreo'
        status_color = '#f59e0b'
    elif failed < total:
        status_class = 'warning'
        status_text = 'Login con Advertencias'
        status_color = '#f59e0b'
    else:
        status_class = 'critical'
        status_text = 'Login con Problemas'
        status_color = '#ef4444'
    
    # Generar filas de tests
    test_rows = ""
    for test in tests:
        status = test.get('status', 'unknown')
        name = test.get('name', 'Test')
        duration = test.get('duration', 0)
        details = test.get('details', {})
        message = details.get('message', details.get('error', ''))
        
        icon = get_status_icon(status)
        badge_class = 'badge-ok' if status in ['ok', 'passed'] else 'badge-error'
        
        test_rows += f'''
        <tr>
            <td>{name}</td>
            <td><span class="badge {badge_class}">{icon} {status.upper()}</span></td>
            <td>{format_duration(duration)}</td>
            <td style="color: var(--text-muted); font-size: 0.875rem;">{message[:80] if message else '-'}</td>
        </tr>'''
    
    # Generar historial
    history_rows = ""
    for run in reversed(history.get('runs', [])[-20:]):
        run_time = run.get('timestamp', '')
        run_time_display = format_chile_timestamp(run_time)
        run_status = run.get('status', 'unknown')
        run_passed = run.get('passed', 0)
        run_total = run.get('total', 0)
        
        icon = get_status_icon(run_status)
        
        history_rows += f'''
        <tr>
            <td>{run_time_display}</td>
            <td>{icon}</td>
            <td>{run_passed}/{run_total}</td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <title>PCFactory Login Monitor</title>
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
        .section-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin: 2rem 0 1rem;
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
            margin-bottom: 2rem;
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
        }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
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
                    <span>Monitor de Login</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <nav class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorias</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link active">🔐 Login</a>
        </nav>
        
        <div class="status-banner {status_class}">
            <span class="status-dot"></span>
            {status_text}
        </div>
        
        <div class="hero-score">
            <div class="score-value">{health_score}%</div>
            <div class="score-label">Tasa de éxito en tests de login</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">TESTS PASADOS</div>
                <div class="stat-value">{passed}/{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">TESTS FALLIDOS</div>
                <div class="stat-value {"error" if failed > 0 else ""}">{failed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">UPTIME 24H</div>
                <div class="stat-value">{uptime_24h}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">EJECUCIONES</div>
                <div class="stat-value">{len(history.get('runs', []))}</div>
            </div>
        </div>
        
        <h2 class="section-title">Detalle de Tests</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Test</th>
                    <th>Estado</th>
                    <th>Duración</th>
                    <th>Detalles</th>
                </tr>
            </thead>
            <tbody>
                {test_rows if test_rows else '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">Sin datos de tests</td></tr>'}
            </tbody>
        </table>
        
        <h2 class="section-title">Historial de Ejecuciones</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Fecha/Hora</th>
                    <th>Estado</th>
                    <th>Resultado</th>
                </tr>
            </thead>
            <tbody>
                {history_rows if history_rows else '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);">Sin historial</td></tr>'}
            </tbody>
        </table>
        
        <footer class="footer">
            <p>Actualización automática: 9am, 2pm, 8pm, 10pm Chile</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='PCFactory Login Dashboard Generator')
    parser.add_argument('--results', type=str, default='./test-results/login-monitor-report.json')
    parser.add_argument('--history', type=str, default=None)
    parser.add_argument('--output-dir', type=str, default='./output')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = args.history or output_dir / 'login-history.json'
    
    results = load_results(args.results)
    if not results:
        print("⚠️ No se encontraron resultados, generando dashboard vacío")
        results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'successRate': 0},
            'overallStatus': 'pending'
        }
    
    history = load_history(history_path)
    
    if results.get('tests'):
        history['runs'].append({
            'timestamp': results.get('timestamp'),
            'status': results.get('overallStatus', 'unknown'),
            'passed': results.get('summary', {}).get('passed', 0),
            'total': results.get('summary', {}).get('total', 0)
        })
        save_history(history, history_path)
    
    html = generate_html(results, history)
    
    output_file = output_dir / 'login.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard generado: {output_file}")
    
    summary = results.get('summary', {})
    print(f"\n📊 Resumen:")
    print(f"   Tests: {summary.get('passed', 0)}/{summary.get('total', 0)} pasados")
    print(f"   Estado: {results.get('overallStatus', 'unknown')}")

if __name__ == '__main__':
    main()
