#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para generar HTML del delivery monitor sin ejecutar el monitor completo
"""
import json
from datetime import datetime, timezone
from delivery_monitor import generate_html_dashboard

# Datos de prueba simulados
test_report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "producto": 53880,
    "total": 554990,
    "tienda_id": 11,
    "cantidad": 1,
    "summary": {
        "total_comunas": 346,
        "disponibles": 320,
        "no_disponibles": 26,
        "errores": 0,
        "promedio_dias": 3.5,
        "dias_distribucion": {3: 150, 4: 100, 5: 50, 7: 20},
        "cobertura_pct": 92.5,
        "total_regiones": 16,
        "despacho_gratis": 45,
        "precio_promedio": 3990,
        "precio_min": 0,
        "precio_max": 11932
    },
    "stats_por_region": {
        13: {
            "nombre": "Metropolitana",
            "total": 52,
            "disponibles": 52,
            "no_disponibles": 0,
            "errores": 0,
            "dias_sum": 156,
            "dias_count": 52,
            "precio_sum": 0,
            "precio_count": 0,
            "gratis_count": 52,
            "cobertura_pct": 100.0,
            "promedio_dias": 3.0,
            "precio_promedio": 0
        },
        5: {
            "nombre": "Valparaíso",
            "total": 38,
            "disponibles": 35,
            "no_disponibles": 3,
            "errores": 0,
            "dias_sum": 140,
            "dias_count": 35,
            "precio_sum": 139650,
            "precio_count": 35,
            "gratis_count": 0,
            "cobertura_pct": 92.1,
            "promedio_dias": 4.0,
            "precio_promedio": 3990
        },
        1: {
            "nombre": "Tarapacá",
            "total": 7,
            "disponibles": 5,
            "no_disponibles": 2,
            "errores": 0,
            "dias_sum": 15,
            "dias_count": 5,
            "precio_sum": 59660,
            "precio_count": 5,
            "gratis_count": 0,
            "cobertura_pct": 71.4,
            "promedio_dias": 3.0,
            "precio_promedio": 11932
        }
    },
    "comunas": [
        # Región Metropolitana (gratis)
        {"id_comuna": 348, "comuna": "ALTO HOSPICIO", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 1, "ciudad": "ALTO HOSPICIO", "estado": "Disponible",
         "fecha_entrega": "2026-01-23", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 11932, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 7, "comuna": "CAMIÑA", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 2, "ciudad": "CAMIÑA", "estado": "Disponible",
         "fecha_entrega": "2026-01-26", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 15702, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 8, "comuna": "COLCHANE", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 3, "ciudad": "COLCHANE", "estado": "Disponible",
         "fecha_entrega": "2026-01-26", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 15702, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 6, "comuna": "HUARA", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 4, "ciudad": "HUARA", "estado": "Disponible",
         "fecha_entrega": "2026-01-26", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 23864, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 5, "comuna": "IQUIQUE", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 5, "ciudad": "IQUIQUE", "estado": "Disponible",
         "fecha_entrega": "2026-01-23", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 11932, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 9, "comuna": "PICA", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 6, "ciudad": "PICA", "estado": "No disponible",
         "fecha_entrega": None, "dias_entrega": None, "transporte": None,
         "precio_despacho": None, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 10, "comuna": "POZO ALMONTE", "id_region": 1, "region": "Tarapacá",
         "id_ciudad": 7, "ciudad": "POZO ALMONTE", "estado": "No disponible",
         "fecha_entrega": None, "dias_entrega": None, "transporte": None,
         "precio_despacho": None, "despacho_gratis": False, "http_code": 200, "url": "..."},

        # Valparaíso (con precio)
        {"id_comuna": 69, "comuna": "VALPARAÍSO", "id_region": 5, "region": "Valparaíso",
         "id_ciudad": 1, "ciudad": "VALPARAÍSO", "estado": "Disponible",
         "fecha_entrega": "2026-01-24", "dias_entrega": 4, "transporte": "Chileexpress",
         "precio_despacho": 3990, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 70, "comuna": "VIÑA DEL MAR", "id_region": 5, "region": "Valparaíso",
         "id_ciudad": 2, "ciudad": "VIÑA DEL MAR", "estado": "Disponible",
         "fecha_entrega": "2026-01-24", "dias_entrega": 4, "transporte": "Chileexpress",
         "precio_despacho": 3990, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 71, "comuna": "CONCÓN", "id_region": 5, "region": "Valparaíso",
         "id_ciudad": 3, "ciudad": "CONCÓN", "estado": "Disponible",
         "fecha_entrega": "2026-01-25", "dias_entrega": 5, "transporte": "Chileexpress",
         "precio_despacho": 3990, "despacho_gratis": False, "http_code": 200, "url": "..."},

        {"id_comuna": 72, "comuna": "QUINTERO", "id_region": 5, "region": "Valparaíso",
         "id_ciudad": 4, "ciudad": "QUINTERO", "estado": "No disponible",
         "fecha_entrega": None, "dias_entrega": None, "transporte": None,
         "precio_despacho": None, "despacho_gratis": False, "http_code": 200, "url": "..."},

        # Metropolitana (gratis)
        {"id_comuna": 119, "comuna": "SANTIAGO", "id_region": 13, "region": "Metropolitana",
         "id_ciudad": 1, "ciudad": "SANTIAGO", "estado": "Disponible",
         "fecha_entrega": "2026-01-23", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 0, "despacho_gratis": True, "http_code": 200, "url": "..."},

        {"id_comuna": 120, "comuna": "LAS CONDES", "id_region": 13, "region": "Metropolitana",
         "id_ciudad": 1, "ciudad": "SANTIAGO", "estado": "Disponible",
         "fecha_entrega": "2026-01-23", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 0, "despacho_gratis": True, "http_code": 200, "url": "..."},

        {"id_comuna": 121, "comuna": "PROVIDENCIA", "id_region": 13, "region": "Metropolitana",
         "id_ciudad": 1, "ciudad": "SANTIAGO", "estado": "Disponible",
         "fecha_entrega": "2026-01-23", "dias_entrega": 3, "transporte": "TurBus",
         "precio_despacho": 0, "despacho_gratis": True, "http_code": 200, "url": "..."},

        {"id_comuna": 122, "comuna": "MAIPÚ", "id_region": 13, "region": "Metropolitana",
         "id_ciudad": 1, "ciudad": "SANTIAGO", "estado": "Disponible",
         "fecha_entrega": "2026-01-24", "dias_entrega": 4, "transporte": "TurBus",
         "precio_despacho": 0, "despacho_gratis": True, "http_code": 200, "url": "..."},

        {"id_comuna": 123, "comuna": "PUENTE ALTO", "id_region": 13, "region": "Metropolitana",
         "id_ciudad": 1, "ciudad": "SANTIAGO", "estado": "Disponible",
         "fecha_entrega": "2026-01-24", "dias_entrega": 4, "transporte": "TurBus",
         "precio_despacho": 0, "despacho_gratis": True, "http_code": 200, "url": "..."},
    ],
    "no_disponibles": [
        {"id_comuna": 9, "comuna": "PICA", "id_region": 1, "region": "Tarapacá", "ciudad": "PICA"},
        {"id_comuna": 10, "comuna": "POZO ALMONTE", "id_region": 1, "region": "Tarapacá", "ciudad": "POZO ALMONTE"},
        {"id_comuna": 72, "comuna": "QUINTERO", "id_region": 5, "region": "Valparaíso", "ciudad": "QUINTERO"},
    ],
    "errores": []
}

if __name__ == "__main__":
    print("🧪 Generando HTML de prueba...")

    # Generar HTML
    html_content = generate_html_dashboard(test_report)

    # Guardar
    output_path = "delivery_test.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML generado: {output_path}")
    print(f"📂 Abre el archivo en tu navegador para probar las nuevas funcionalidades")
    print(f"\n💡 Características a probar:")
    print("   - Click en encabezados de columnas para ordenar")
    print("   - Filtros por Estado, Días y Precio")
    print("   - Búsqueda por texto")
    print("   - Botón 'Limpiar Filtros'")
    print("   - Contador dinámico de comunas visibles")
