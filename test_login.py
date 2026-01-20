#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para generar HTML del login dashboard
"""
import json
import sys
from datetime import datetime, timezone, timedelta

# Add login scripts to path
sys.path.insert(0, 'login/scripts')
from login_dashboard import generate_html

# Datos de prueba - Resultados actuales
test_results = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "status": "passed",
    "summary": {
        "total": 6,
        "passed": 6,
        "failed": 0,
        "warnings": 0,
        "successRate": 100
    },
    "tests": [
        {
            "name": "Página principal carga correctamente",
            "status": "passed",
            "duration": 1.9
        },
        {
            "name": "Formulario de login visible",
            "status": "passed",
            "duration": 0.5
        },
        {
            "name": "Login con credenciales válidas",
            "status": "passed",
            "duration": 2.3
        },
        {
            "name": "Redirección post-login",
            "status": "passed",
            "duration": 1.1
        },
        {
            "name": "Sesión persistente",
            "status": "passed",
            "duration": 0.8
        },
        {
            "name": "Logout funcional",
            "status": "passed",
            "duration": 1.2
        }
    ]
}

# Historial de prueba (solo 1 ejecución anterior)
test_history = {
    "runs": [
        {
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
            "status": "passed",
            "passed": 6,
            "total": 6
        }
    ]
}

if __name__ == "__main__":
    print("🧪 Generando HTML de prueba para Login Dashboard...")

    # Generar HTML
    html_content = generate_html(test_results, test_history)

    # Guardar
    output_path = "login_test.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML generado: {output_path}")
    print(f"📱 Abre el archivo en tu navegador y verás:")
    print(f"\n💡 Cambios realizados:")
    print("   - ✅ 'Ejecuciones (Total): 2' - Clarifica que es el total acumulado")
    print("   - ✅ Historial muestra 2 filas: La ejecución actual + 1 anterior")
    print("   - ✅ El contador de historial es fijo: 'Últimas 15 ejecuciones'")
    print("\n📊 Antes solo mostraba 1 fila aunque decía '2 ejecuciones'")
