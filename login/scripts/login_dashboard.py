#!/usr/bin/env python3
"""
PCFactory Login Monitor - Generador de Dashboard CON VIDEO
Genera un dashboard HTML con los resultados del monitoreo de login.
VERSIÓN DE PRUEBA CON REPRODUCTOR DE VIDEO
"""

import json
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


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

def find_results_file(base_path):
    """Busca el archivo de resultados en múltiples ubicaciones."""
    possible_paths = [
        base_path,
        Path(base_path),
        Path('login/test-results/login-monitor-report.json'),
        Path('./login/test-results/login-monitor-report.json'),
        Path('test-results/login-monitor-report.json'),
        Path('./test-results/login-monitor-report.json'),
    ]

    print(f"🔍 Buscando archivo de resultados...")
    print(f"   Directorio actual: {os.getcwd()}")

    for p in possible_paths:
        path = Path(p)
        print(f"   Probando: {path} ... ", end="")
        if path.exists():
            print(f"✅ ENCONTRADO")
            return path
        else:
            print(f"❌ no existe")

    # Buscar recursivamente
    print(f"   Buscando recursivamente...")
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'login-monitor-report.json':
                found_path = Path(root) / file
                print(f"   ✅ Encontrado en: {found_path}")
                return found_path

    return None

def load_results(results_path):
    """Carga los resultados del test."""
    path = find_results_file(results_path)

    if not path:
        print(f"⚠️ No se encontró el archivo de resultados")
        return None

    try:
        print(f"📄 Cargando: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"   Keys en JSON: {list(data.keys())}")

        if 'suites' in data:
            print(f"   Formato: Playwright reporter")
            return parse_playwright_format(data)
        elif 'tests' in data:
            print(f"   Formato: Custom")
            return data
        else:
            print(f"   Formato: Desconocido")
            return data

    except Exception as e:
        print(f"❌ Error cargando resultados: {e}")
        return None

def parse_playwright_format(data):
    """Convierte formato Playwright a formato esperado CON VIDEOS."""
    tests = []

    print(f"   Parsing Playwright format con videos...")

    def process_suite(suite, depth=0):
        """Procesa un suite recursivamente."""
        # Procesar specs directamente en este suite
        for spec in suite.get('specs', []):
            spec_title = spec.get('title', 'Unknown Spec')

            # Cada spec puede tener múltiples tests (por proyecto/browser)
            for test in spec.get('tests', []):
                status_raw = test.get('status', 'unknown')

                # Mapear estados de Playwright
                if status_raw == 'expected':
                    status = 'passed'
                elif status_raw == 'skipped':
                    status = 'warning'
                elif status_raw in ['unexpected', 'failed']:
                    status = 'failed'
                else:
                    status = 'warning'

                # Obtener duración y attachments del primer resultado
                duration = 0
                video_path = ""
                results = test.get('results', [])
                if results:
                    duration = results[0].get('duration', 0)
                    # Buscar video en attachments
                    for attachment in results[0].get('attachments', []):
                        if attachment.get('contentType') == 'video/webm':
                            # La ruta es relativa a /home/runner/work/pcfactory-monitor/pcfactory-monitor/login/
                            # Necesitamos convertirla a una ruta relativa al HTML
                            full_path = attachment.get('path', '')
                            if full_path:
                                # Extraer toda la ruta después de login/ para mantener estructura única
                                if 'test-results/' in full_path:
                                    # Mantener estructura completa: videos/test-results/hash-nombre/video.webm
                                    video_subpath = full_path.split('test-results/')[-1]
                                    relative_path = 'videos/test-results/' + video_subpath
                                    video_path = relative_path
                                    print(f"      Video encontrado: {video_path}")

                tests.append({
                    'name': spec_title,
                    'status': status,
                    'duration': duration,
                    'video_path': video_path,
                    'details': {'projectName': test.get('projectName', '')}
                })

        # Procesar suites anidados
        for nested_suite in suite.get('suites', []):
            process_suite(nested_suite, depth + 1)

    # Procesar todos los suites de nivel superior
    for suite in data.get('suites', []):
        process_suite(suite)

    passed = len([t for t in tests if t['status'] == 'passed'])
    failed = len([t for t in tests if t['status'] == 'failed'])
    warnings = len([t for t in tests if t['status'] == 'warning'])
    total = len(tests)

    print(f"   Parsed {total} tests: {passed} passed, {failed} failed, {warnings} warnings")
    print(f"   Videos encontrados: {len([t for t in tests if t.get('video_path')])}")

    return {
        'timestamp': datetime.now().isoformat(),
        'tests': tests,
        'summary': {
            'total': total,
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'successRate': round((passed / total) * 100) if total > 0 else 0
        },
        'overallStatus': 'ok' if failed == 0 and total > 0 else ('warning' if warnings > 0 else 'error')
    }

def load_history(history_path):
    """Carga el historial de ejecuciones anteriores."""
    try:
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error cargando historial: {e}")
    return {'runs': []}

def save_history(history, history_path):
    """Guarda el historial actualizado."""
    history['runs'] = history['runs'][-100:]
    os.makedirs(os.path.dirname(history_path) if os.path.dirname(history_path) else '.', exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_status_icon(status):
    """Retorna el ícono según el estado."""
    icons = {
        'ok': '✅', 'passed': '✅',
        'error': '❌', 'failed': '❌',
        'warning': '⚠️', 'pending': '⏳'
    }
    return icons.get(status, '❓')

def get_status_class(status):
    """Retorna la clase CSS según el estado."""
    classes = {
        'ok': 'green', 'passed': 'green',
        'error': 'red', 'failed': 'red',
        'warning': 'yellow', 'pending': 'blue'
    }
    return classes.get(status, '')

def format_duration(ms):
    """Formatea la duración en formato legible."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}min"

def generate_html(results, history):
    """Genera el HTML del dashboard CON REPRODUCTOR DE VIDEO."""

    timestamp = results.get('timestamp', datetime.now().isoformat())
    tests = results.get('tests', [])
    summary = results.get('summary', {})
    overall_status = results.get('overallStatus', 'pending')

    # Formatear timestamp - usar hora Chile
    timestamp_display = format_chile_timestamp(timestamp)

    # Calcular uptime 24h
    recent_runs = []
    now = datetime.now()
    for r in history.get('runs', []):
        try:
            run_time = datetime.fromisoformat(r.get('timestamp', '2000-01-01').replace('Z', '+00:00'))
            if (now - run_time.replace(tzinfo=None)).total_seconds() < 86400:
                recent_runs.append(r)
        except:
            pass

    if recent_runs:
        ok_runs = len([r for r in recent_runs if r.get('status') in ['ok', 'passed']])
        uptime_24h = (ok_runs / len(recent_runs)) * 100
    else:
        uptime_24h = 100 if overall_status in ['ok', 'passed'] else 0

    # Estadísticas
    passed = summary.get('passed', 0)
    total = summary.get('total', 0)
    failed = summary.get('failed', 0)
    warnings = summary.get('warnings', 0)
    health_score = summary.get('successRate', 0)

    # Determinar estado y colores
    if overall_status in ['ok', 'passed'] or (total > 0 and failed == 0):
        status_class = 'healthy'
        status_text = 'Login Operativo'
        status_color = 'var(--accent-green)'
    elif overall_status == 'warning' or (total > 0 and failed < total):
        status_class = 'warning'
        status_text = 'Login con Advertencias'
        status_color = 'var(--accent-yellow)'
    elif total == 0:
        status_class = 'warning'
        status_text = 'Sin datos de monitoreo'
        status_color = 'var(--accent-yellow)'
    else:
        status_class = 'critical'
        status_text = 'Login con Problemas'
        status_color = 'var(--accent-red)'

    # Generar filas de tests CON BOTÓN DE VIDEO
    test_rows = ""
    for test in tests:
        status = test.get('status', 'unknown')
        name = test.get('name', 'Test')
        duration = test.get('duration', 0)
        video_path = test.get('video_path', '')
        details = test.get('details', {})
        message = details.get('message', details.get('error', ''))

        status_badge_class = get_status_class(status)

        # Botón de video si existe
        video_button = ""
        if video_path:
            video_button = f'''
                <button class="video-btn" onclick="openVideoModal('{video_path}', '{name}')">
                    <span class="video-icon">🎬</span> Ver video
                </button>'''

        test_rows += f"""
                <tr>
                    <td><span class="badge badge-id">{name}</span></td>
                    <td><span class="stat-value {status_badge_class}" style="font-size: 0.875rem;">{get_status_icon(status)} {status.upper()}</span></td>
                    <td><span class="badge">{format_duration(duration)}</span></td>
                    <td style="color: var(--text-secondary);">
                        {message[:60] if message else '-'}
                        {video_button}
                    </td>
                </tr>
        """

    if not test_rows:
        test_rows = '<tr><td colspan="4" class="empty-state">Sin datos de tests</td></tr>'

    # Generar historial (incluyendo ejecución actual)
    history_rows = ""

    # Primero agregar la ejecución actual
    current_run = {
        'timestamp': results.get('timestamp', datetime.now(timezone.utc).isoformat()),
        'status': overall_status,
        'passed': passed,
        'total': total
    }

    # Combinar ejecución actual con historial previo
    all_runs = [current_run] + list(reversed(history.get('runs', [])[-14:]))

    for run in all_runs:
        run_time = run.get('timestamp', '')
        run_status = run.get('status', 'unknown')
        run_passed = run.get('passed', 0)
        run_total = run.get('total', 0)

        try:
            dt = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
            dt_chile = utc_to_chile(dt)
            formatted_time = dt_chile.strftime('%d/%m %H:%M')
        except:
            formatted_time = run_time[:16] if run_time else 'N/A'

        status_badge_class = get_status_class(run_status)

        history_rows += f"""
                <tr>
                    <td>{formatted_time}</td>
                    <td><span class="stat-value {status_badge_class}" style="font-size: 0.875rem;">{get_status_icon(run_status)}</span></td>
                    <td><span class="badge badge-id">{run_passed}/{run_total}</span></td>
                </tr>
        """

    if not history_rows:
        history_rows = '<tr><td colspan="3" class="empty-state">Sin historial</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCFactory Login Monitor</title>
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
            min-height: 100vh;
            line-height: 1.6;
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
        .status-banner.critical {{ border-color: var(--accent-red); background: rgba(239, 68, 68, 0.1); }}
        .status-banner.warning {{ border-color: var(--accent-yellow); background: rgba(245, 158, 11, 0.1); }}
        .status-banner.healthy {{ border-color: var(--accent-green); background: rgba(16, 185, 129, 0.1); }}
        .status-indicator {{
            width: 12px; height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        .status-banner.critical .status-indicator {{ background: var(--accent-red); }}
        .status-banner.warning .status-indicator {{ background: var(--accent-yellow); }}
        .status-banner.healthy .status-indicator {{ background: var(--accent-green); }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
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
        .badge {{
            font-family: var(--font-mono);
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        .badge-id {{ background: var(--bg-hover); color: var(--text-secondary); }}
        .empty-state {{ padding: 3rem; text-align: center; color: var(--text-muted); }}

        /* Estilos del botón de video */
        .video-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-left: 1rem;
            padding: 0.5rem 1rem;
            background: var(--accent-blue);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 0.75rem;
            font-family: var(--font-mono);
            cursor: pointer;
            transition: all 0.2s;
        }}
        .video-btn:hover {{
            background: #2563eb;
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
            max-width: 90vw;
            max-height: 90vh;
            position: relative;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .video-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        .video-modal-header h3 {{ font-size: 1.1rem; }}
        .video-modal-close {{
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
            transition: color 0.2s;
        }}
        .video-modal-close:hover {{ color: var(--text-primary); }}
        .video-modal video {{
            width: 100%;
            height: auto;
            max-height: calc(90vh - 120px);
            max-width: 1200px;
            border-radius: 8px;
            object-fit: contain;
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
                    <span>Monitor de Login</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>

        <div class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="checkout.html" class="nav-link">🛒 Checkout</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link active">🔐 Login</a>
            <a href="banners.html" class="nav-link">🎨 Banners</a>
        </div>

        <div class="status-banner {status_class}">
            <div class="status-indicator"></div>
            <span class="status-text">{status_text}</span>
        </div>

        <div class="health-card">
            <div class="health-score">{health_score}%</div>
            <div class="health-label">Tasa de éxito en tests de login</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Tests Pasados</div>
                <div class="stat-value green">{passed}/{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Tests Fallidos</div>
                <div class="stat-value {'red' if failed > 0 else 'green'}">{failed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Uptime 24h</div>
                <div class="stat-value {'green' if uptime_24h >= 90 else 'yellow' if uptime_24h >= 70 else 'red'}">{uptime_24h:.0f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Ejecuciones (Total)</div>
                <div class="stat-value blue">{len(history.get('runs', [])) + 1}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <h2>📋 Resultados de Tests</h2>
                <span class="section-count">{total} tests</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Test</th>
                            <th>Estado</th>
                            <th>Duración</th>
                            <th>Detalles</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <h2>📊 Historial Reciente</h2>
                <span class="section-count">Últimas 15 ejecuciones</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Estado</th>
                            <th>Tests</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="footer">
            <p>Actualización automática 3 veces al día (9am, 2pm, 8pm Chile)</p>
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
        // Funciones del modal de video
        function openVideoModal(videoPath, testName) {{
            const modal = document.getElementById('videoModal');
            const video = document.getElementById('videoPlayer');
            const title = document.getElementById('videoModalTitle');

            title.textContent = 'Test: ' + testName;
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

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Genera dashboard de Login Monitor CON VIDEO')
    parser.add_argument('--results', default='test-results/login-monitor-report.json',
                        help='Ruta al archivo de resultados JSON')
    parser.add_argument('--output-dir', default='./output',
                        help='Directorio de salida para el dashboard')
    parser.add_argument('--history', default=None,
                        help='Ruta al archivo de historial')

    args = parser.parse_args()

    print(f"🚀 Generando dashboard de Login Monitor CON VIDEO")
    print(f"   Args: {args}")

    # Crear directorio de salida
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ruta del historial
    history_path = args.history or str(output_dir / 'login-history.json')

    # Cargar resultados
    results = load_results(args.results)
    if not results:
        print("⚠️ No se encontraron resultados, generando dashboard vacío")
        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'successRate': 0},
            'overallStatus': 'pending'
        }
    else:
        print(f"✅ Resultados cargados: {results.get('summary', {})}")

    # Cargar historial
    history = load_history(history_path)

    # Agregar ejecución actual al historial (evitar duplicados por minuto)
    if results.get('tests'):
        current_timestamp = results.get('timestamp')
        # Verificar si ya existe una entrada en el mismo minuto (truncar a minuto para comparar)
        try:
            current_dt = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            current_minute = current_dt.replace(second=0, microsecond=0).isoformat()
            existing = False
            for run in history['runs']:
                try:
                    run_dt = datetime.fromisoformat(run.get('timestamp', '').replace('Z', '+00:00'))
                    run_minute = run_dt.replace(second=0, microsecond=0).isoformat()
                    if run_minute == current_minute:
                        existing = True
                        break
                except:
                    continue
        except:
            # Si falla el parsing, usar comparación exacta como fallback
            existing = any(run.get('timestamp') == current_timestamp for run in history['runs'])

        if not existing:
            history['runs'].append({
                'timestamp': current_timestamp,
                'status': results.get('overallStatus', 'unknown'),
                'passed': results.get('summary', {}).get('passed', 0),
                'total': results.get('summary', {}).get('total', 0)
            })
            save_history(history, history_path)

    # Generar HTML
    html = generate_html(results, history)

    # Guardar dashboard
    output_file = output_dir / 'login.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard generado: {output_file}")

    # Mostrar resumen
    summary = results.get('summary', {})
    print(f"\n📊 Resumen:")
    print(f"   Tests: {summary.get('passed', 0)}/{summary.get('total', 0)} pasados")
    print(f"   Estado: {results.get('overallStatus', 'unknown')}")

if __name__ == '__main__':
    main()
