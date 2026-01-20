#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para el sistema de historial de categorías
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Simular datos de prueba
def create_test_data():
    now = datetime.now(timezone.utc)

    # Crear reporte simulado
    report = {
        "timestamp": now.isoformat(),
        "summary": {
            "total_categorias": 389,
            "urls_ok": 389,
            "urls_error": 0,
            "con_productos": 389,
            "sin_productos": 0,
            "health_score": 100
        },
        "resultados": [
            {"id": 1, "nombre": "Procesadores", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 150, "url": "https://www.pcfactory.cl/procesadores", "elapsed_ms": 250},
            {"id": 2, "nombre": "Placas Madre", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 200, "url": "https://www.pcfactory.cl/placas-madre", "elapsed_ms": 300},
            {"id": 3, "nombre": "Memorias RAM", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 180, "url": "https://www.pcfactory.cl/memorias-ram", "elapsed_ms": 280},
            {"id": 4, "nombre": "Tarjetas Gráficas", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 120, "url": "https://www.pcfactory.cl/tarjetas-graficas", "elapsed_ms": 320},
            {"id": 5, "nombre": "Nueva Categoría 1", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 50, "url": "https://www.pcfactory.cl/nueva-cat-1", "elapsed_ms": 200},
            {"id": 6, "nombre": "Nueva Categoría 2", "ok": True, "status_code": 200, "tiene_productos": True, "total_productos": 30, "url": "https://www.pcfactory.cl/nueva-cat-2", "elapsed_ms": 220},
        ],
        "categorias_con_errores": [],
        "categorias_vacias": [],
        "comparison": {
            "new": [
                {"id": 5, "nombre": "Nueva Categoría 1", "status_code": 200, "total_productos": 50, "url": "https://www.pcfactory.cl/nueva-cat-1"},
                {"id": 6, "nombre": "Nueva Categoría 2", "status_code": 200, "total_productos": 30, "url": "https://www.pcfactory.cl/nueva-cat-2"}
            ],
            "removed": [
                {"id": 99, "nombre": "Categoría Eliminada 1"},
                {"id": 100, "nombre": "Categoría Eliminada 2"}
            ],
            "new_count": 2,
            "removed_count": 2
        }
    }

    # Crear historial simulado (últimas 5 ejecuciones)
    history = {
        "history": [
            {
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "total_categories": 387,
                "added": [],
                "removed": []
            },
            {
                "timestamp": (now - timedelta(days=3)).isoformat(),
                "total_categories": 387,
                "added": [
                    {"id": 7, "nombre": "Categoría Antigua 1", "timestamp": (now - timedelta(days=3)).isoformat()}
                ],
                "removed": []
            },
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "total_categories": 388,
                "added": [],
                "removed": [
                    {"id": 99, "nombre": "Categoría Eliminada 1", "timestamp": (now - timedelta(days=2)).isoformat()},
                    {"id": 100, "nombre": "Categoría Eliminada 2", "timestamp": (now - timedelta(days=2)).isoformat()}
                ]
            },
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "total_categories": 386,
                "added": [],
                "removed": []
            },
            {
                "timestamp": now.isoformat(),
                "total_categories": 389,
                "added": [
                    {"id": 5, "nombre": "Nueva Categoría 1", "timestamp": now.isoformat()},
                    {"id": 6, "nombre": "Nueva Categoría 2", "timestamp": now.isoformat()}
                ],
                "removed": []
            }
        ]
    }

    report["history"] = history

    return report

if __name__ == "__main__":
    print("🧪 Generando datos de prueba para sistema de historial de categorías...\n")

    # Importar función de generación de dashboard
    from monitor import generate_html_dashboard

    # Crear datos de prueba
    test_report = create_test_data()

    print(f"📊 Datos generados:")
    print(f"   - Total categorías: {test_report['summary']['total_categorias']}")
    print(f"   - Categorías nuevas: {test_report['comparison']['new_count']}")
    print(f"   - Categorías eliminadas: {test_report['comparison']['removed_count']}")
    print(f"   - Historial: {len(test_report['history']['history'])} ejecuciones")

    # Generar HTML
    html_content = generate_html_dashboard(test_report)

    # Guardar
    output_path = Path("categories_history_test.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n✅ HTML generado: {output_path}")
    print(f"\n💡 Funcionalidades a probar:")
    print("   1. ✅ Ver 2 tarjetas nuevas: '📈 Agregadas' y '📉 Eliminadas'")
    print("   2. ✅ Hacer clic en cada tarjeta para ver detalles")
    print("   3. ✅ Ver timestamps de cuándo se agregaron/eliminaron")
    print("   4. ✅ Cerrar las secciones con el botón X")
    print("   5. ✅ Las tarjetas muestran el total del historial (no solo la última ejecución)")

    print(f"\n📂 Abre el archivo en tu navegador para ver el resultado!")
