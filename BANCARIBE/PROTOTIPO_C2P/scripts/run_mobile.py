#!/usr/bin/env python3
"""
Servidor para app móvil Bancaribe PWA
"""

import sys
import os
from pathlib import Path
import http.server
import socketserver
import webbrowser
import threading

# Directorio de la app móvil
MOBILE_DIR = Path(__file__).parent.parent / "mobile"

class MobileHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(MOBILE_DIR), **kwargs)
    
    def handle_one_request(self):
        try:
            return super().handle_one_request()
        except (ConnectionResetError, ConnectionAbortedError):
            pass
    
    def log_message(self, format, *args):
        pass

def open_browser():
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:8081')

def main():
    port = 8081
    
    print("=" * 60)
    print("BANCARIBE - APP MOVIL PWA")
    print("=" * 60)
    print(f"\nDirectorio mobile: {MOBILE_DIR}")
    print(f"App URL: http://localhost:{port}")
    print(f"API Backend: http://localhost:8000")
    print("\nPresiona Ctrl+C para detener...")
    print("=" * 60 + "\n")
    
    if not MOBILE_DIR.exists():
        print(f"Error: No existe el directorio mobile: {MOBILE_DIR}")
        sys.exit(1)
    
    if not (MOBILE_DIR / "index.html").exists():
        print(f"Error: No existe index.html en {MOBILE_DIR}")
        sys.exit(1)
    
    with socketserver.TCPServer(("", port), MobileHandler) as httpd:
        # Abrir navegador en thread separado
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")

if __name__ == "__main__":
    main()
