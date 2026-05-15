"""
Servidor WebSocket para actualizaciones en tiempo real del dashboard
"""

import asyncio
import json
import websockets
import threading
from datetime import datetime
from typing import Set, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    Servidor WebSocket para broadcast de actualizaciones de transacciones
    Permite dashboard en tiempo real con métricas y estado de transacciones
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = False
        self.server = None
        self.loop = None
        self.thread: threading.Thread = None
        self.message_queue = asyncio.Queue()
        
    async def _register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Registra nuevo cliente conectado"""
        self.clients.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.clients)}")
        
        # Enviar mensaje de bienvenida
        welcome = {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Conectado al dashboard C2P Bancaribe"
        }
        await websocket.send(json.dumps(welcome))
        
    async def _unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Elimina cliente desconectado"""
        self.clients.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.clients)}")
        
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Maneja conexión individual con cliente"""
        await self._register_client(websocket)
        try:
            async for message in websocket:
                # Procesar mensajes entrantes del cliente
                try:
                    data = json.loads(message)
                    await self._process_client_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Mensaje JSON inválido"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self._unregister_client(websocket)
            
    async def _process_client_message(self, websocket: websockets.WebSocketServerProtocol, data: Dict[str, Any]):
        """Procesa mensajes recibidos de clientes"""
        msg_type = data.get("type", "unknown")
        
        if msg_type == "ping":
            await websocket.send(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
        elif msg_type == "subscribe":
            channel = data.get("channel", "all")
            await websocket.send(json.dumps({
                "type": "subscribed",
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            }))
        elif msg_type == "get_metrics":
            # Solicitar métricas al motor de conciliación
            await websocket.send(json.dumps({
                "type": "metrics_request",
                "timestamp": datetime.now().isoformat()
            }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Tipo de mensaje no soportado: {msg_type}"
            }))
            
    async def _broadcast_worker(self):
        """Worker para broadcast de mensajes"""
        while self.running:
            try:
                # Timeout para permitir chequeo de running
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                if self.clients:
                    # Broadcast a todos los clientes conectados
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send(json.dumps(message))
                        except websockets.exceptions.ConnectionClosed:
                            disconnected.add(client)
                        except Exception as e:
                            logger.error(f"Error enviando a cliente: {e}")
                            disconnected.add(client)
                    
                    # Limpiar clientes desconectados
                    for client in disconnected:
                        self.clients.discard(client)
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error en broadcast worker: {e}")
                
    async def _start_server(self):
        """Inicia el servidor WebSocket"""
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info(f"Servidor WebSocket iniciado en ws://{self.host}:{self.port}")
        
        # Iniciar worker de broadcast
        broadcast_task = asyncio.create_task(self._broadcast_worker())
        
        # Mantener servidor corriendo
        await self.server.wait_closed()
        
        # Cancelar worker cuando se cierra
        broadcast_task.cancel()
        try:
            await broadcast_task
        except asyncio.CancelledError:
            pass
            
    def start(self):
        """Inicia el servidor en un thread separado"""
        if self.running:
            logger.warning("Servidor WebSocket ya está corriendo")
            return
            
        self.running = True
        
        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._start_server())
            
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        logger.info("Thread del servidor WebSocket iniciado")
        
    def stop(self):
        """Detiene el servidor WebSocket"""
        if not self.running:
            return
            
        self.running = False
        
        if self.server:
            self.server.close()
            
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        if self.thread:
            self.thread.join(timeout=5.0)
            
        logger.info("Servidor WebSocket detenido")
        
    def broadcast_transaction_update(self, tx_data: Dict[str, Any]):
        """
        Envía actualización de transacción a todos los clientes conectados
        Thread-safe - puede llamarse desde cualquier thread
        """
        message = {
            "type": "transaction_update",
            "transaction_id": tx_data.get("transaction_id"),
            "state": tx_data.get("state"),
            "merchant_id": tx_data.get("merchant_id"),
            "amount": tx_data.get("amount"),
            "timestamp": datetime.now().isoformat()
        }
        self.broadcast(message)
    
    def broadcast(self, message: Dict[str, Any]):
        """
        Envía mensaje a todos los clientes conectados
        Thread-safe - puede llamarse desde cualquier thread
        """
        if not self.running or not self.loop:
            return
            
        # Agregar timestamp si no existe
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
            
        # Agregar a cola de manera thread-safe
        asyncio.run_coroutine_threadsafe(
            self.message_queue.put(message),
            self.loop
        )
        
    def broadcast_transaction_update(self, transaction_id: str, state: str, 
                                     metadata: Dict[str, Any] = None):
        """Broadcast específico para actualizaciones de transacciones"""
        message = {
            "type": "transaction_update",
            "transaction_id": transaction_id,
            "state": state,
            "metadata": metadata or {}
        }
        self.broadcast(message)
        
    def broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast de métricas del sistema"""
        message = {
            "type": "metrics_update",
            "metrics": metrics
        }
        self.broadcast(message)
        
    def broadcast_alert(self, alert_type: str, message: str, severity: str = "info"):
        """Broadcast de alertas del sistema"""
        msg = {
            "type": "alert",
            "alert_type": alert_type,
            "message": message,
            "severity": severity
        }
        self.broadcast(msg)
        
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servidor"""
        return {
            "connected_clients": len(self.clients),
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "queue_size": self.message_queue.qsize() if self.loop else 0
        }


# Instancia global para fácil acceso
_global_ws_server: WebSocketServer = None


def get_global_server() -> WebSocketServer:
    """Obtiene instancia global del servidor WebSocket"""
    global _global_ws_server
    if _global_ws_server is None:
        _global_ws_server = WebSocketServer()
    return _global_ws_server


def broadcast_transaction(transaction_id: str, state: str, metadata: Dict[str, Any] = None):
    """Helper global para broadcast de transacciones"""
    server = get_global_server()
    if server.running:
        server.broadcast_transaction_update(transaction_id, state, metadata)


def broadcast_system_metrics(metrics: Dict[str, Any]):
    """Helper global para broadcast de métricas"""
    server = get_global_server()
    if server.running:
        server.broadcast_metrics(metrics)


def broadcast_system_alert(alert_type: str, message: str, severity: str = "info"):
    """Helper global para broadcast de alertas"""
    server = get_global_server()
    if server.running:
        server.broadcast_alert(alert_type, message, severity)
