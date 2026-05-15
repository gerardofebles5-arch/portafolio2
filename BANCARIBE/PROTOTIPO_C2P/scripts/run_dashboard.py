#!/usr/bin/env python3
"""
Servidor del Dashboard Frontend para MVP Conciliación C2P
Sirve el dashboard HTML en localhost:8080
"""

import sys
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser

# Directorio del frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def handle_one_request(self):
        try:
            return super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError):
            pass  # Browser closed connection, ignore
    
    def log_message(self, format, *args):
        # Silenciar logs de peticiones
        pass


def open_browser():
    """Abre el navegador después de un pequeño delay"""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:8080')


def main():
    port = 8080
    
    print("=" * 60)
    print("BANCARIBE C2P - Dashboard de Conciliacion")
    print("=" * 60)
    print(f"\nDirectorio frontend: {FRONTEND_DIR}")
    print(f"Dashboard URL: http://localhost:{port}")
    print(f"API Backend: http://localhost:8000")
    print(f"WebSocket: ws://localhost:8765")
    print("\nAsegúrate de que el servidor API esté corriendo:")
    print("   python scripts/run_server.py")
    print("\nPresiona Ctrl+C para detener...")
    print("=" * 60 + "\n")
    
    # Verificar que existe el frontend
    if not FRONTEND_DIR.exists():
        print(f"❌ Error: No existe el directorio frontend: {FRONTEND_DIR}")
        sys.exit(1)
    
    if not (FRONTEND_DIR / "index.html").exists():
        print(f"❌ Error: No existe index.html en {FRONTEND_DIR}")
        sys.exit(1)
    
    # Abrir navegador automáticamente
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Iniciar servidor
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido")
        server.shutdown()


if __name__ == "__main__":
    main()
