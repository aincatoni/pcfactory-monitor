#!/usr/bin/env python3
"""
Script de prueba para el dashboard de login CON VIDEO
"""

import sys
import os

# Agregar el directorio login/scripts al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'login', 'scripts'))

# Importar el nuevo dashboard con video
from login_dashboard_with_video import main

if __name__ == '__main__':
    print("🧪 Probando dashboard de login CON VIDEO...")
    print("=" * 60)

    # Ejecutar con los argumentos predeterminados
    sys.argv = [
        'test_login_with_video.py',
        '--results', './login/test-results/login-monitor-report.json',
        '--output-dir', './output'
    ]

    main()

    print("=" * 60)
    print("✅ Prueba completada!")
    print("📂 Abre el archivo: output/login_with_video.html")
