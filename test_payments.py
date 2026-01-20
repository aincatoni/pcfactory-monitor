#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para generar HTML del payments dashboard
"""
import json
from datetime import datetime, timezone
from payment_dashboard import generate_html_dashboard

# Datos de prueba
test_results = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "total": 5,
        "passed": 4,
        "failed": 1
    },
    "results": [
        {
            "paymentMethod": "Transferencia ETPay",
            "status": "passed",
            "duration": 12.5,
            "videoPath": "videos/etpay.webm",
            "error": None
        },
        {
            "paymentMethod": "Compraquí",
            "status": "passed",
            "duration": 8.3,
            "videoPath": "videos/compraqui.webm",
            "error": None
        },
        {
            "paymentMethod": "Mastercard Click to Pay",
            "status": "failed",
            "duration": 15.2,
            "videoPath": "videos/mastercard.webm",
            "error": "Timeout esperando elemento de pago"
        },
        {
            "paymentMethod": "Tarjeta de Débito (Webpay)",
            "status": "passed",
            "duration": 10.1,
            "videoPath": "videos/debito.webm",
            "error": None
        },
        {
            "paymentMethod": "Tarjeta de Crédito (Webpay)",
            "status": "passed",
            "duration": 10.8,
            "videoPath": "videos/credito.webm",
            "error": None
        }
    ]
}

# Historial de prueba (últimas 10 ejecuciones)
test_history = [
    {
        "timestamp": "2026-01-20T14:03:00Z",
        "passed": 5,
        "failed": 0,
        "total": 5
    },
    {
        "timestamp": "2026-01-20T09:00:00Z",
        "passed": 4,
        "failed": 1,
        "total": 5
    },
    {
        "timestamp": "2026-01-19T20:00:00Z",
        "passed": 5,
        "failed": 0,
        "total": 5
    },
    {
        "timestamp": "2026-01-19T14:00:00Z",
        "passed": 5,
        "failed": 0,
        "total": 5
    },
    {
        "timestamp": "2026-01-19T09:00:00Z",
        "passed": 3,
        "failed": 2,
        "total": 5
    },
]

if __name__ == "__main__":
    print("🧪 Generando HTML de prueba para Payments Dashboard...")

    # Generar HTML
    html_content = generate_html_dashboard(test_results, test_history)

    # Guardar
    output_path = "payments_test.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML generado: {output_path}")
    print(f"📱 Abre el archivo en tu navegador y pruébalo en modo mobile (responsive)")
    print(f"\n💡 Para probarlo en mobile:")
    print("   1. Abre el archivo en Chrome/Firefox")
    print("   2. Presiona F12 para abrir DevTools")
    print("   3. Presiona Ctrl+Shift+M (Cmd+Shift+M en Mac) para toggle device toolbar")
    print("   4. Selecciona iPhone 14 o similar")
    print("   5. Revisa la sección 'Historial de Verificaciones' - ahora tiene scroll horizontal")
