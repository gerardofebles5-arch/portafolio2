#!/usr/bin/env python3
"""
Configurar ngrok para exponer servicios online
"""

from pyngrok import ngrok
import sys
import time

print("=" * 60)
print("CONFIGURANDO ACCESO ONLINE")
print("=" * 60)

# Crear túnel para API (port 8000)
print("\n[1/3] Creando túnel para API (port 8000)...")
api_tunnel = ngrok.connect(8000)
print(f"API URL: {api_tunnel.public_url}")

# Crear túnel para Dashboard (port 8080)
print("\n[2/3] Creando túnel para Dashboard (port 8080)...")
dashboard_tunnel = ngrok.connect(8080)
print(f"Dashboard URL: {dashboard_tunnel.public_url}")

# Crear túnel para App Móvil (port 8081)
print("\n[3/3] Creando túnel para App Móvil (port 8081)...")
mobile_tunnel = ngrok.connect(8081)
print(f"App Móvil URL: {mobile_tunnel.public_url}")

print("\n" + "=" * 60)
print("SERVICIOS ONLINE")
print("=" * 60)
print(f"API: {api_tunnel.public_url}")
print(f"Dashboard: {dashboard_tunnel.public_url}")
print(f"App Móvil: {mobile_tunnel.public_url}")
print("=" * 60)
print("\nPresiona Ctrl+C para detener los túneles...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nDeteniendo túneles...")
    ngrok.kill()
    print("Túneles detenidos")
