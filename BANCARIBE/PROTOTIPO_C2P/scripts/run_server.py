#!/usr/bin/env python3
"""
Servidor principal del MVP Conciliación C2P
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.main import app

if __name__ == "__main__":
    import uvicorn
    
    print("Iniciando servidor API MVP Conciliacion C2P")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("Metrics: http://localhost:8000/metrics")
    print("\nPresione Ctrl+C para detener...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
