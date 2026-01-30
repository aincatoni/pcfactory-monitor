#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCFactory PageSpeed Monitor
Monitorea Core Web Vitals usando Google PageSpeed Insights API
"""
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests


# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# API de PageSpeed Insights (sin API key tiene límite de 25 requests/día)
PAGESPEED_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# URL a monitorear
TARGET_URL = "https://www.pcfactory.cl"

# Categorías a analizar
CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]

# Estrategias (mobile y desktop)
STRATEGIES = ["mobile", "desktop"]


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
# API CALLS
# ==============================================================================

def run_pagespeed_test(url: str, strategy: str = "mobile", api_key: Optional[str] = None) -> Dict:
    """
    Ejecuta test de PageSpeed Insights

    Args:
        url: URL a analizar
        strategy: "mobile" o "desktop"
        api_key: API key de Google (opcional, pero recomendado para más requests)

    Returns:
        Dict con resultados completos de la API
    """
    params = {
        "url": url,
        "strategy": strategy,
        "category": CATEGORIES
    }

    if api_key:
        params["key"] = api_key

    print(f"  🔍 Analizando {strategy}...")

    try:
        response = requests.get(PAGESPEED_API_URL, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ❌ Error al analizar {strategy}: {e}")
        return None


def extract_metrics(pagespeed_data: Dict) -> Dict:
    """
    Extrae métricas importantes de la respuesta de PageSpeed

    Returns:
        Dict con métricas simplificadas
    """
    if not pagespeed_data:
        return None

    try:
        lighthouse = pagespeed_data.get("lighthouseResult", {})
        audits = lighthouse.get("audits", {})
        categories = lighthouse.get("categories", {})

        # Core Web Vitals
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000  # ms -> s
        fid = audits.get("max-potential-fid", {}).get("numericValue", 0)  # ms
        cls = audits.get("cumulative-layout-shift", {}).get("numericValue", 0)

        # Otras métricas importantes
        fcp = audits.get("first-contentful-paint", {}).get("numericValue", 0) / 1000  # ms -> s
        tti = audits.get("interactive", {}).get("numericValue", 0) / 1000  # ms -> s
        speed_index = audits.get("speed-index", {}).get("numericValue", 0) / 1000  # ms -> s
        tbt = audits.get("total-blocking-time", {}).get("numericValue", 0)  # ms

        # Scores (0-100)
        performance_score = categories.get("performance", {}).get("score", 0) * 100
        accessibility_score = categories.get("accessibility", {}).get("score", 0) * 100
        best_practices_score = categories.get("best-practices", {}).get("score", 0) * 100
        seo_score = categories.get("seo", {}).get("score", 0) * 100

        return {
            # Core Web Vitals
            "lcp": round(lcp, 2),
            "fid": round(fid, 1),
            "cls": round(cls, 3),

            # Otras métricas
            "fcp": round(fcp, 2),
            "tti": round(tti, 2),
            "speed_index": round(speed_index, 2),
            "tbt": round(tbt, 1),

            # Scores
            "performance_score": round(performance_score, 1),
            "accessibility_score": round(accessibility_score, 1),
            "best_practices_score": round(best_practices_score, 1),
            "seo_score": round(seo_score, 1)
        }
    except Exception as e:
        print(f"  ⚠️  Error extrayendo métricas: {e}")
        return None


# ==============================================================================
# HISTORIAL
# ==============================================================================

def load_history(history_path: Path) -> List[Dict]:
    """Carga historial de mediciones"""
    if history_path.exists():
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(history: List[Dict], history_path: Path):
    """Guarda historial de mediciones"""
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_to_history(history: List[Dict], new_data: Dict, max_entries: int = 90) -> List[Dict]:
    """
    Agrega nueva medición al historial

    Args:
        history: Historial actual
        new_data: Nueva medición
        max_entries: Máximo de entradas a mantener (default: 90 días)

    Returns:
        Historial actualizado
    """
    history.append(new_data)

    # Mantener solo las últimas N entradas
    if len(history) > max_entries:
        history = history[-max_entries:]

    return history


# ==============================================================================
# MONITOR PRINCIPAL
# ==============================================================================

def run_pagespeed_monitor(url: str, api_key: Optional[str] = None,
                          output_dir: Path = Path("./output"),
                          history_path: Optional[Path] = None) -> Dict:
    """
    Ejecuta monitor de PageSpeed completo

    Args:
        url: URL a monitorear
        api_key: API key de Google (opcional)
        output_dir: Directorio de salida
        history_path: Path al archivo de historial

    Returns:
        Dict con resultados completos
    """
    print(f"[*] PageSpeed Monitor para: {url}")
    print(f"[*] Timestamp: {datetime.now(timezone.utc).isoformat()}")

    now = datetime.now(timezone.utc)

    results = {
        "timestamp": now.isoformat(),
        "url": url,
        "mobile": None,
        "desktop": None
    }

    # Analizar mobile
    mobile_data = run_pagespeed_test(url, "mobile", api_key)
    if mobile_data:
        results["mobile"] = extract_metrics(mobile_data)
        print(f"  ✅ Mobile: Performance {results['mobile']['performance_score']:.0f}/100")

    # Esperar un poco entre requests
    time.sleep(2)

    # Analizar desktop
    desktop_data = run_pagespeed_test(url, "desktop", api_key)
    if desktop_data:
        results["desktop"] = extract_metrics(desktop_data)
        print(f"  ✅ Desktop: Performance {results['desktop']['performance_score']:.0f}/100")

    # Cargar y actualizar historial
    if history_path is None:
        history_path = output_dir / "pagespeed_history.json"

    history = load_history(history_path)
    history = add_to_history(history, results)
    save_history(history, history_path)

    print(f"\n[+] Historial actualizado: {len(history)} mediciones")

    return {
        "current": results,
        "history": history
    }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="PCFactory PageSpeed Monitor")
    parser.add_argument("--url", type=str, default=TARGET_URL, help="URL a monitorear")
    parser.add_argument("--api-key", type=str, default=None, help="Google PageSpeed API key (opcional)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directorio de salida")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PCFactory PageSpeed Monitor - Core Web Vitals")
    print("=" * 60)

    # Ejecutar monitor
    report = run_pagespeed_monitor(
        url=args.url,
        api_key=args.api_key,
        output_dir=output_dir
    )

    # Guardar JSON completo
    json_path = output_dir / "pagespeed_report.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[+] Reporte guardado: {json_path}")

    # Resumen
    current = report["current"]
    print("\n" + "=" * 60)
    print("RESUMEN CORE WEB VITALS")
    print("=" * 60)

    for strategy in ["mobile", "desktop"]:
        if current.get(strategy):
            metrics = current[strategy]
            print(f"\n{strategy.upper()}:")
            print(f"  Performance Score: {metrics['performance_score']:.0f}/100")
            print(f"  LCP: {metrics['lcp']:.2f}s")
            print(f"  FID: {metrics['fid']:.0f}ms")
            print(f"  CLS: {metrics['cls']:.3f}")

    print("\n[OK] Monitor completado!")


if __name__ == "__main__":
    main()
