#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera dashboard HTML para métricas de PageSpeed
"""
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta


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


def get_cwv_status(metric_name, value):
    """
    Determina el estado de una métrica Core Web Vital

    Returns:
        tuple: (class_name, status_text)
    """
    if metric_name == "lcp":
        if value < 2.5:
            return "good", "Bueno"
        elif value < 4.0:
            return "needs-improvement", "Mejorable"
        else:
            return "poor", "Pobre"
    elif metric_name == "fid":
        if value < 100:
            return "good", "Bueno"
        elif value < 300:
            return "needs-improvement", "Mejorable"
        else:
            return "poor", "Pobre"
    elif metric_name == "cls":
        if value < 0.1:
            return "good", "Bueno"
        elif value < 0.25:
            return "needs-improvement", "Mejorable"
        else:
            return "poor", "Pobre"
    return "unknown", "Desconocido"


def generate_html_dashboard(report: dict, output_dir: Path):
    """Genera dashboard HTML con métricas de PageSpeed"""

    current = report.get("current", {})
    history = report.get("history", [])

    timestamp_display = format_chile_timestamp(current.get("timestamp", ""))

    # Datos actuales (manejar None si la API falló)
    mobile = current.get("mobile") or {}
    desktop = current.get("desktop") or {}

    # Verificar si hay datos válidos
    has_data = bool(mobile) or bool(desktop)
    data_warning = ""
    if not has_data:
        data_warning = '''
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--accent-yellow); border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;">
            <h3 style="color: var(--accent-yellow); margin-bottom: 0.5rem;">⚠️ Sin datos disponibles</h3>
            <p style="color: var(--text-secondary); margin: 0;">
                No se pudieron obtener datos de la API de PageSpeed Insights.
                Esto puede deberse a límites de rate, problemas de red, o que aún no se ha ejecutado el monitor.
                El próximo análisis se ejecutará automáticamente a las 12pm Chile.
            </p>
        </div>
        '''

    # Preparar datos para gráficos (últimos 30 días)
    history_data = history[-30:] if len(history) > 30 else history

    # Extraer series de tiempo
    timestamps = []
    mobile_perf = []
    desktop_perf = []
    mobile_lcp = []
    desktop_lcp = []
    mobile_cls = []
    desktop_cls = []

    for entry in history_data:
        try:
            dt = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
            timestamps.append(dt.strftime('%d/%m'))

            if entry.get("mobile"):
                mobile_perf.append(entry["mobile"].get("performance_score", 0))
                mobile_lcp.append(entry["mobile"].get("lcp", 0))
                mobile_cls.append(entry["mobile"].get("cls", 0))
            else:
                mobile_perf.append(None)
                mobile_lcp.append(None)
                mobile_cls.append(None)

            if entry.get("desktop"):
                desktop_perf.append(entry["desktop"].get("performance_score", 0))
                desktop_lcp.append(entry["desktop"].get("lcp", 0))
                desktop_cls.append(entry["desktop"].get("cls", 0))
            else:
                desktop_perf.append(None)
                desktop_lcp.append(None)
                desktop_cls.append(None)
        except:
            continue

    # Status CWV
    mobile_lcp_status, mobile_lcp_text = get_cwv_status("lcp", mobile.get("lcp", 0)) if mobile else ("unknown", "N/A")
    mobile_fid_status, mobile_fid_text = get_cwv_status("fid", mobile.get("fid", 0)) if mobile else ("unknown", "N/A")
    mobile_cls_status, mobile_cls_text = get_cwv_status("cls", mobile.get("cls", 0)) if mobile else ("unknown", "N/A")

    desktop_lcp_status, desktop_lcp_text = get_cwv_status("lcp", desktop.get("lcp", 0)) if desktop else ("unknown", "N/A")
    desktop_fid_status, desktop_fid_text = get_cwv_status("fid", desktop.get("fid", 0)) if desktop else ("unknown", "N/A")
    desktop_cls_status, desktop_cls_text = get_cwv_status("cls", desktop.get("cls", 0)) if desktop else ("unknown", "N/A")

    # Promedio de performance score
    mobile_valid = [p for p in mobile_perf if p is not None]
    avg_mobile_perf = sum(mobile_valid) / len(mobile_valid) if mobile_valid else 0

    desktop_valid = [p for p in desktop_perf if p is not None]
    avg_desktop_perf = sum(desktop_valid) / len(desktop_valid) if desktop_valid else 0

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="86400">
    <title>PCFactory PageSpeed Monitor - Core Web Vitals</title>
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

        .cwv-status {{
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
        }}
        .cwv-status.good {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
        .cwv-status.needs-improvement {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}
        .cwv-status.poor {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); }}

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
        .section-content {{ padding: 1.5rem; }}

        .chart-container {{
            position: relative;
            height: 300px;
            margin-bottom: 1.5rem;
        }}

        .footer {{ text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem; }}

        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
                    <span>Core Web Vitals - PageSpeed Insights</span>
                </div>
            </div>
            <div class="timestamp">{timestamp_display}</div>
        </header>

        <div class="nav-links">
            <a href="index.html" class="nav-link">📦 Categorías</a>
            <a href="delivery.html" class="nav-link">🚚 Despacho Nacional</a>
            <a href="checkout.html" class="nav-link">🛒 Checkout</a>
            <a href="payments.html" class="nav-link">💳 Medios de Pago</a>
            <a href="login.html" class="nav-link">🔐 Login</a>
            <a href="banners.html" class="nav-link">🎨 Banners</a>
            <a href="pagespeed.html" class="nav-link active">⚡ PageSpeed</a>
        </div>

        {data_warning}

        <h3 style="margin-bottom: 1rem; font-size: 1.25rem;">📱 Mobile</h3>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Performance Score</div>
                <div class="stat-value {'green' if mobile.get('performance_score', 0) >= 90 else 'yellow' if mobile.get('performance_score', 0) >= 50 else 'red'}">{mobile.get('performance_score', 0):.0f}/100</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">LCP (Largest Contentful Paint)</div>
                <div class="stat-value">{mobile.get('lcp', 0):.2f}s</div>
                <div class="cwv-status {mobile_lcp_status}">{mobile_lcp_text}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">FID (First Input Delay)</div>
                <div class="stat-value">{mobile.get('fid', 0):.0f}ms</div>
                <div class="cwv-status {mobile_fid_status}">{mobile_fid_text}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">CLS (Cumulative Layout Shift)</div>
                <div class="stat-value">{mobile.get('cls', 0):.3f}</div>
                <div class="cwv-status {mobile_cls_status}">{mobile_cls_text}</div>
            </div>
        </div>

        <h3 style="margin-bottom: 1rem; font-size: 1.25rem;">💻 Desktop</h3>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Performance Score</div>
                <div class="stat-value {'green' if desktop.get('performance_score', 0) >= 90 else 'yellow' if desktop.get('performance_score', 0) >= 50 else 'red'}">{desktop.get('performance_score', 0):.0f}/100</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">LCP (Largest Contentful Paint)</div>
                <div class="stat-value">{desktop.get('lcp', 0):.2f}s</div>
                <div class="cwv-status {desktop_lcp_status}">{desktop_lcp_text}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">FID (First Input Delay)</div>
                <div class="stat-value">{desktop.get('fid', 0):.0f}ms</div>
                <div class="cwv-status {desktop_fid_status}">{desktop_fid_text}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">CLS (Cumulative Layout Shift)</div>
                <div class="stat-value">{desktop.get('cls', 0):.3f}</div>
                <div class="cwv-status {desktop_cls_status}">{desktop_cls_text}</div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>📊</span>
                <h2>Historial Performance Score (últimos 30 días)</h2>
            </div>
            <div class="section-content">
                <div class="chart-container">
                    <canvas id="perfChart"></canvas>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>⚡</span>
                <h2>Historial LCP - Largest Contentful Paint (últimos 30 días)</h2>
            </div>
            <div class="section-content">
                <div class="chart-container">
                    <canvas id="lcpChart"></canvas>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span>📐</span>
                <h2>Historial CLS - Cumulative Layout Shift (últimos 30 días)</h2>
            </div>
            <div class="section-content">
                <div class="chart-container">
                    <canvas id="clsChart"></canvas>
                </div>
            </div>
        </div>

        <footer class="footer">
            <p>Actualización automática cada 24 horas</p>
            <p>Datos de Google PageSpeed Insights API</p>
            <p>Hecho con ❤️ por Ain Cortés Catoni</p>
        </footer>
    </div>

    <script>
        const chartConfig = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    labels: {{ color: '#a1a1aa', font: {{ family: 'Ubuntu' }} }}
                }}
            }},
            scales: {{
                y: {{
                    grid: {{ color: '#27272a' }},
                    ticks: {{ color: '#a1a1aa' }}
                }},
                x: {{
                    grid: {{ color: '#27272a' }},
                    ticks: {{ color: '#a1a1aa' }}
                }}
            }}
        }};

        // Performance Score Chart
        new Chart(document.getElementById('perfChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{
                        label: 'Mobile',
                        data: {json.dumps(mobile_perf)},
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.3
                    }},
                    {{
                        label: 'Desktop',
                        data: {json.dumps(desktop_perf)},
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3
                    }}
                ]
            }},
            options: {{
                ...chartConfig,
                scales: {{
                    ...chartConfig.scales,
                    y: {{
                        ...chartConfig.scales.y,
                        min: 0,
                        max: 100
                    }}
                }}
            }}
        }});

        // LCP Chart
        new Chart(document.getElementById('lcpChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{
                        label: 'Mobile (segundos)',
                        data: {json.dumps(mobile_lcp)},
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.3
                    }},
                    {{
                        label: 'Desktop (segundos)',
                        data: {json.dumps(desktop_lcp)},
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3
                    }}
                ]
            }},
            options: {{
                ...chartConfig,
                plugins: {{
                    ...chartConfig.plugins,
                    annotation: {{
                        annotations: {{
                            good: {{
                                type: 'line',
                                yMin: 2.5,
                                yMax: 2.5,
                                borderColor: '#10b981',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {{ content: 'Bueno: < 2.5s', enabled: true, color: '#10b981' }}
                            }},
                            poor: {{
                                type: 'line',
                                yMin: 4.0,
                                yMax: 4.0,
                                borderColor: '#ef4444',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {{ content: 'Pobre: > 4s', enabled: true, color: '#ef4444' }}
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // CLS Chart
        new Chart(document.getElementById('clsChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(timestamps)},
                datasets: [
                    {{
                        label: 'Mobile',
                        data: {json.dumps(mobile_cls)},
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.3
                    }},
                    {{
                        label: 'Desktop',
                        data: {json.dumps(desktop_cls)},
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.3
                    }}
                ]
            }},
            options: chartConfig
        }});
    </script>
</body>
</html>'''

    html_path = output_dir / "pagespeed.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[+] Dashboard generado: {html_path}")
    return html_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=str, required=True, help="Path al archivo de resultados JSON")
    parser.add_argument("--output-dir", type=str, default="./output")
    args = parser.parse_args()

    results_path = Path(args.results)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar resultados
    with open(results_path, 'r') as f:
        report = json.load(f)

    # Generar dashboard
    generate_html_dashboard(report, output_dir)


if __name__ == "__main__":
    main()
