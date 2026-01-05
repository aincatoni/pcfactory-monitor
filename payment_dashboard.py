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
# FUNCIONES DE CARGA Y PROCESAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════

def load_results(results_path: str) -> Dict:
    """Carga los resultados del test de Playwright."""
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[!] Archivo no encontrado: {results_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"[!] Error parsing JSON: {e}")
        return None

def load_history(history_path: str) -> List[Dict]:
    """Carga el historial de ejecuciones previas."""
    try:
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(history: List[Dict], history_path: str):
    """Guarda el historial actualizado."""
    history = history[-50:]
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

def generate_html_dashboard(results: Dict, history: List[Dict]) -> str:
    """Genera el dashboard HTML completo."""
    timestamp = results.get("timestamp", datetime.now(timezone.utc).isoformat())
    timestamp_display = format_chile_timestamp(timestamp)
    
    payment_results = results.get("results", [])
    summary = results.get("summary", {"total": 0, "passed": 0, "failed": 0})
    
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    
    # Determinar estado
    if total == 0:
        status_class = "warning"
        status_text = "Sin datos de monitoreo"
        status_color = "#f59e0b"
        health_pct = 0
    elif failed == 0:
        status_class = "healthy"
        status_text = "Todos los medios de pago operativos"
        status_color = "#10b981"
        health_pct = 100
    elif failed < total:
        status_class = "warning"
        status_text = f"{failed} medio(s) con problemas"
        status_color = "#f59e0b"
        health_pct = round((passed / total) * 100, 1)
    else:
        status_class = "critical"
        status_text = "Todos los medios con problemas"
        status_color = "#ef4444"
        health_pct = 0
    
    # Generar cards de medios de pago
    payment_cards = ""
    for r in payment_results:
        method = r.get("paymentMethod", "Desconocido")
        status = r.get("status", "UNKNOWN")
        duration = r.get("duration", 0)
        
        if status == "PASSED":
            card_class = "card-ok"
            icon = "✅"
            badge_class = "badge-ok"
            badge_text = "Operativo"
        else:
            card_class = "card-error"
            icon = "❌"
            badge_class = "badge-error"
            badge_text = "Con Problemas"
        
        duration_str = f"{duration}ms" if duration < 1000 else f"{duration/1000:.1f}s"
        
        payment_cards += f'''
        <div class="payment-card {card_class}">
            <div class="payment-icon">{icon}</div>
            <div class="payment-name">{method}</div>
            <span class="badge {badge_class}">{badge_text}</span>
        </div>'''
    
    # Generar historial
    history_rows = ""
    for entry in reversed(history[-20:]):
        ts = entry.get("timestamp", "")
        ts_display = format_chile_timestamp(ts)
        entry_results = entry.get("results", [])
        entry_summary = entry.get("summary", {})
        
        statuses = ""
        for r in entry_results:
            icon = "✅" if r.get("status") == "PASSED" else "❌"
            statuses += f'<span title="{r.get("paymentMethod", "")}">{icon}</span> '
        
        history_rows += f'''
        <tr>
            <td>{ts_display}</td>
            <td class="status-icons">{statuses}</td>
            <td>{entry_summary.get("passed", 0)}/{entry_summary.get("total", 0)}</td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <title>PCFactory - Monitor de Medios de Pago</title>
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
            text-align: center;
            border: 1px solid var(--border);
        }}
        .stat-value {{
            font-family: var(--font-mono);
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent-green);
        }}
        .stat-value.warning {{ color: var(--accent-yellow); }}
        .stat-value.error {{ color: var(--accent-red); }}
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
        }}
        .section-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}
        .payments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .payment-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
        }}
        .payment-card.card-ok {{ border-color: var(--accent-green); }}
        .payment-card.card-error {{ border-color: var(--accent-red); }}
        .payment-icon {{ font-size: 2rem; }}
        .payment-name {{ font-weight: 500; text-align: center; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .badge-ok {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .badge-error {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}
        .history-table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .history-table th, .history-table td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        .history-table th {{
            background: var(--bg-secondary);
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-muted);
        }}
        .history-table tr:last-child td {{ border-bottom: none; }}
        .status-icons {{ font-size: 1rem; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .stat-value {{ font-size: 2rem; }}
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
                    <span>Medios de Pago</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>
        
        <nav class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorias</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="payments.html" class="nav-link active">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
        </nav>
        
        <div class="status-banner {status_class}">
            <span class="status-dot"></span>
            {status_text}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Medios</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{passed}</div>
                <div class="stat-label">Operativos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {"error" if failed > 0 else ""}">{failed}</div>
                <div class="stat-label">Con Problemas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: {status_color}">{health_pct}%</div>
                <div class="stat-label">Disponibilidad</div>
            </div>
        </div>
        
        <h2 class="section-title">Estado de Medios de Pago</h2>
        <div class="payments-grid">
            {payment_cards if payment_cards else '<p style="color: var(--text-muted);">No hay datos disponibles</p>'}
        </div>
        
        <h2 class="section-title">Historial de Verificaciones</h2>
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
    parser = argparse.ArgumentParser(description="PCFactory Payment Dashboard Generator")
    parser.add_argument("--results", type=str, default="./test-results/payment-monitor-report.json")
    parser.add_argument("--output-dir", type=str, default="./output")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PCFactory Payment Dashboard Generator")
    print("=" * 60)
    
    results = load_results(args.results)
    if not results:
        print(f"[!] No se encontró archivo de resultados: {args.results}")
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "summary": {"total": 0, "passed": 0, "failed": 0}
        }
    
    history_path = output_dir / "payment_history.json"
    history = load_history(str(history_path))
    
    if results.get("results"):
        history.append({
            "timestamp": results.get("timestamp"),
            "results": results.get("results"),
            "summary": results.get("summary")
        })
        save_history(history, str(history_path))
    
    html_content = generate_html_dashboard(results, history)
    html_path = output_dir / "payments.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Dashboard guardado: {html_path}")
    
    summary = results.get("summary", {})
    print(f"\nTotal medios: {summary.get('total', 0)}")
    print(f"Operativos: {summary.get('passed', 0)}")
    print(f"Con problemas: {summary.get('failed', 0)}")
    print("\n[OK] Dashboard generado!")

if __name__ == "__main__":
    main()
