#!/usr/bin/env python3
"""
PCFactory Login Monitor - Generador de Dashboard
Genera un dashboard HTML con los resultados del monitoreo de login.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

def load_results(results_path):
    """Carga los resultados del test de Playwright."""
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando resultados: {e}")
        return None

def load_history(history_path):
    """Carga el historial de ejecuciones anteriores."""
    try:
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando historial: {e}")
    return {'runs': []}

def save_history(history, history_path):
    """Guarda el historial actualizado."""
    # Mantener solo las últimas 100 ejecuciones
    history['runs'] = history['runs'][-100:]
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_status_icon(status):
    """Retorna el ícono según el estado."""
    icons = {
        'ok': '✅',
        'passed': '✅',
        'error': '❌',
        'failed': '❌',
        'warning': '⚠️',
        'pending': '⏳'
    }
    return icons.get(status, '❓')

def get_status_class(status):
    """Retorna la clase CSS según el estado."""
    classes = {
        'ok': 'status-ok',
        'passed': 'status-ok',
        'error': 'status-error',
        'failed': 'status-error',
        'warning': 'status-warning',
        'pending': 'status-pending'
    }
    return classes.get(status, 'status-unknown')

def format_duration(ms):
    """Formatea la duración en formato legible."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}min"

def generate_html(results, history):
    """Genera el HTML del dashboard."""
    
    timestamp = results.get('timestamp', datetime.now().isoformat())
    tests = results.get('tests', [])
    summary = results.get('summary', {})
    overall_status = results.get('overallStatus', 'unknown')
    
    # Calcular uptime de las últimas 24 horas
    recent_runs = [r for r in history.get('runs', []) 
                   if datetime.fromisoformat(r.get('timestamp', '2000-01-01').replace('Z', '+00:00')) 
                   > datetime.now().astimezone() - __import__('datetime').timedelta(hours=24)]
    
    if recent_runs:
        ok_runs = len([r for r in recent_runs if r.get('status') == 'ok'])
        uptime_24h = (ok_runs / len(recent_runs)) * 100
    else:
        uptime_24h = 100 if overall_status == 'ok' else 0
    
    # Generar filas de tests
    test_rows = ""
    for test in tests:
        status = test.get('status', 'unknown')
        name = test.get('name', 'Test')
        duration = test.get('duration', 0)
        details = test.get('details', {})
        message = details.get('message', details.get('error', ''))
        
        test_rows += f"""
        <tr>
            <td class="test-name">{name}</td>
            <td class="{get_status_class(status)}">{get_status_icon(status)} {status.upper()}</td>
            <td>{format_duration(duration)}</td>
            <td class="test-details">{message[:100] if message else '-'}</td>
        </tr>
        """
    
    # Generar historial reciente
    history_rows = ""
    for run in reversed(history.get('runs', [])[-20:]):
        run_time = run.get('timestamp', '')
        run_status = run.get('status', 'unknown')
        run_passed = run.get('passed', 0)
        run_total = run.get('total', 0)
        
        try:
            dt = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%d/%m %H:%M')
        except:
            formatted_time = run_time[:16]
        
        history_rows += f"""
        <tr>
            <td>{formatted_time}</td>
            <td class="{get_status_class(run_status)}">{get_status_icon(run_status)}</td>
            <td>{run_passed}/{run_total}</td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PCFactory Login Monitor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 2rem;
            color: #fff;
            margin-bottom: 10px;
        }}
        
        .nav-buttons {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .nav-btn {{
            padding: 10px 20px;
            background: #2d3748;
            color: #e0e0e0;
            text-decoration: none;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            border: 1px solid #4a5568;
        }}
        
        .nav-btn:hover {{
            background: #4a5568;
            transform: translateY(-2px);
        }}
        
        .nav-btn.active {{
            background: #9f7aea;
            border-color: #9f7aea;
            color: #fff;
        }}
        
        .status-banner {{
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.5rem;
            font-weight: bold;
        }}
        
        .status-banner.ok {{
            background: linear-gradient(135deg, #22543d 0%, #276749 100%);
            border: 2px solid #48bb78;
        }}
        
        .status-banner.error {{
            background: linear-gradient(135deg, #742a2a 0%, #9b2c2c 100%);
            border: 2px solid #fc8181;
        }}
        
        .status-banner.warning {{
            background: linear-gradient(135deg, #744210 0%, #975a16 100%);
            border: 2px solid #f6ad55;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #fff;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: #a0aec0;
            margin-top: 5px;
        }}
        
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .card h2 {{
            font-size: 1.2rem;
            margin-bottom: 15px;
            color: #fff;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        th {{
            color: #a0aec0;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}
        
        .test-name {{
            font-weight: 500;
        }}
        
        .test-details {{
            font-size: 0.85rem;
            color: #a0aec0;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .status-ok {{ color: #48bb78; }}
        .status-error {{ color: #fc8181; }}
        .status-warning {{ color: #f6ad55; }}
        .status-pending {{ color: #a0aec0; }}
        
        .timestamp {{
            text-align: center;
            color: #718096;
            font-size: 0.85rem;
            margin-top: 30px;
        }}
        
        .screenshots {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .screenshot {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }}
        
        .screenshot img {{
            max-width: 100%;
            border-radius: 4px;
        }}
        
        .screenshot-label {{
            font-size: 0.8rem;
            color: #a0aec0;
            margin-top: 8px;
        }}
        
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.5rem; }}
            .stat-value {{ font-size: 2rem; }}
            .nav-btn {{ padding: 8px 15px; font-size: 0.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔐 PCFactory Login Monitor</h1>
            <p>Monitoreo del sistema de autenticación</p>
        </header>
        
        <nav class="nav-buttons">
            <a href="index.html" class="nav-btn">📦 Categorías</a>
            <a href="delivery.html" class="nav-btn">🚚 Despacho</a>
            <a href="payments.html" class="nav-btn">💳 Medios de Pago</a>
            <a href="login.html" class="nav-btn active">🔐 Login</a>
        </nav>
        
        <div class="status-banner {overall_status}">
            {get_status_icon(overall_status)} Login {
                'Operativo' if overall_status == 'ok' 
                else 'Con Problemas' if overall_status == 'error' 
                else 'Advertencias'
            }
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{summary.get('passed', 0)}/{summary.get('total', 0)}</div>
                <div class="stat-label">Tests Pasados</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary.get('successRate', 0)}%</div>
                <div class="stat-label">Tasa de Éxito</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{uptime_24h:.0f}%</div>
                <div class="stat-label">Uptime 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(history.get('runs', []))}</div>
                <div class="stat-label">Ejecuciones</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 Resultados de Tests</h2>
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
                    {test_rows if test_rows else '<tr><td colspan="4" style="text-align:center">Sin datos</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📊 Historial Reciente</h2>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Estado</th>
                        <th>Tests</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows if history_rows else '<tr><td colspan="3" style="text-align:center">Sin historial</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <p class="timestamp">
            Última actualización: {datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M:%S') if timestamp else 'N/A'}
        </p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Genera dashboard de Login Monitor')
    parser.add_argument('--results', default='test-results/login-monitor-report.json',
                        help='Ruta al archivo de resultados JSON')
    parser.add_argument('--output-dir', default='./output',
                        help='Directorio de salida para el dashboard')
    parser.add_argument('--history', default=None,
                        help='Ruta al archivo de historial')
    
    args = parser.parse_args()
    
    # Crear directorio de salida
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ruta del historial
    history_path = args.history or output_dir / 'login-history.json'
    
    # Cargar resultados
    results = load_results(args.results)
    if not results:
        print("⚠️ No se encontraron resultados, generando dashboard vacío")
        results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {'total': 0, 'passed': 0, 'failed': 0, 'successRate': 0},
            'overallStatus': 'pending'
        }
    
    # Cargar historial
    history = load_history(history_path)
    
    # Agregar ejecución actual al historial
    if results.get('tests'):
        history['runs'].append({
            'timestamp': results.get('timestamp'),
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
