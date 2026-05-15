"""
API FastAPI para el MVP Conciliación C2P
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

try:
    from ..storage.event_store import EventStore
    from ..retry_queue.retry_queue import RetryQueue
    from ..engine.reconciliation import C2PReconciliationEngine, PaymentRequest
    from ..websocket.server import WebSocketServer
except ImportError:
    from storage.event_store import EventStore
    from retry_queue.retry_queue import RetryQueue
    from engine.reconciliation import C2PReconciliationEngine, PaymentRequest
    from websocket.server import WebSocketServer


# Modelos Pydantic para API
class PaymentRequestModel(BaseModel):
    qr_data: str
    merchant_id: str
    amount: float
    customer_id: str
    reference: Optional[str] = None


class TransactionResponse(BaseModel):
    transaction_id: str
    status: str
    message: str


class TransactionStatusResponse(BaseModel):
    transaction_id: str
    current_state: str
    merchant_id: str
    amount: float
    created_at: str
    last_updated: str
    processing_time_ms: int
    retry_count: int
    is_duplicate: bool


class MetricsResponse(BaseModel):
    period: Dict[str, str]
    total_transactions: int
    completed: int
    failed: int
    processing: int
    initiated: int
    success_rate: float
    failure_rate: float
    pending_transactions: int
    processed_by_engine: int
    failed_by_engine: int
    engine_success_rate: float
    retry_queue_stats: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    components: Dict[str, str]


# Inicializar aplicación FastAPI
app = FastAPI(
    title="Bancaribe C2P Conciliation API",
    description="MVP para conciliación de transacciones Pago Móvil C2P",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar componentes globales
event_store = EventStore()
retry_queue = RetryQueue(max_retries=3, base_delay=1.0)
reconciliation_engine = C2PReconciliationEngine(event_store, retry_queue)
ws_server = WebSocketServer(host="localhost", port=8765)


# @app.on_event("startup")
# async def startup_event():
#     """Evento de inicio de la aplicación"""
#     print("Bancaribe C2P API starting up...")
#     # ws_server.start()  # Temporalmente desactivado


# @app.on_event("shutdown")
# async def shutdown_event():
#     """Evento de apagado de la aplicación"""
#     ws_server.stop()
#     reconciliation_engine.shutdown()
#     event_store.close()
#     print("Bancaribe C2P API shutdown complete")


@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint raíz"""
    return {
        "message": "Bancaribe C2P Conciliation API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        components={
            "event_store": "healthy",
            "retry_queue": "healthy" if retry_queue.running else "stopped",
            "reconciliation_engine": "healthy"
        }
    )


@app.post("/transactions", response_model=TransactionResponse)
async def create_transaction(payment_request: PaymentRequestModel):
    """
    Crea una nueva transacción de pago C2P
    """
    try:
        # Convertir modelo de Pydantic a objeto interno
        payment_obj = PaymentRequest(
            qr_data=payment_request.qr_data,
            merchant_id=payment_request.merchant_id,
            amount=payment_request.amount,
            customer_id=payment_request.customer_id,
            reference=payment_request.reference
        )
        
        # Iniciar transacción
        transaction_id = reconciliation_engine.initiate_payment(payment_obj)
        
        # Notificar al WebSocket (temporalmente desactivado)
        # ws_server.broadcast_transaction_update({
        #     "transaction_id": transaction_id,
        #     "state": "initiated",
        #     "merchant_id": payment_obj.merchant_id,
        #     "amount": payment_obj.amount
        # })
        
        return TransactionResponse(
            transaction_id=transaction_id,
            status="initiated",
            message="Transaction initiated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")


@app.get("/transactions/{transaction_id}", response_model=TransactionStatusResponse)
async def get_transaction_status(transaction_id: str):
    """
    Obtiene el estado de una transacción específica
    """
    try:
        summary = reconciliation_engine.get_transaction_status(transaction_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return TransactionStatusResponse(
            transaction_id=summary.transaction_id,
            current_state=summary.current_state.value,
            merchant_id=summary.merchant_id,
            amount=summary.amount,
            created_at=summary.created_at.isoformat(),
            last_updated=summary.last_updated.isoformat(),
            processing_time_ms=summary.processing_time_ms,
            retry_count=summary.retry_count,
            is_duplicate=summary.is_duplicate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction status: {str(e)}")


@app.get("/transactions", response_model=List[TransactionStatusResponse])
async def get_recent_transactions(limit: int = 10):
    """
    Obtiene transacciones recientes
    """
    try:
        if limit > 100:
            limit = 100  # Limitar máximo
        
        summaries = reconciliation_engine.get_recent_transactions(limit)
        
        return [
            TransactionStatusResponse(
                transaction_id=summary.transaction_id,
                current_state=summary.current_state.value,
                merchant_id=summary.merchant_id,
                amount=summary.amount,
                created_at=summary.created_at.isoformat(),
                last_updated=summary.last_updated.isoformat(),
                processing_time_ms=summary.processing_time_ms,
                retry_count=summary.retry_count,
                is_duplicate=summary.is_duplicate
            )
            for summary in summaries
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent transactions: {str(e)}")


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Obtiene métricas del sistema
    """
    try:
        metrics = reconciliation_engine.get_metrics()
        
        return MetricsResponse(**metrics)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@app.post("/simulate/bulk-payments")
async def simulate_bulk_payments(count: int = 50):
    """
    Simula procesamiento masivo de pagos para testing
    """
    try:
        if count > 1000:
            count = 1000  # Limitar máximo
        
        transaction_ids = reconciliation_engine.simulate_bulk_payments(count)
        
        return {
            "message": f"Bulk payment simulation started",
            "transaction_count": len(transaction_ids),
            "transaction_ids": transaction_ids[:10],  # Mostrar primeros 10
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate bulk payments: {str(e)}")


@app.get("/simulate/status")
async def get_simulation_status():
    """
    Obtiene estado actual de la simulación
    """
    try:
        metrics = reconciliation_engine.get_metrics()
        
        return {
            "pending_transactions": metrics["pending_transactions"],
            "processed_by_engine": metrics["processed_by_engine"],
            "failed_by_engine": metrics["failed_by_engine"],
            "engine_success_rate": metrics["engine_success_rate"],
            "retry_queue_stats": metrics["retry_queue_stats"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get simulation status: {str(e)}")


@app.post("/simulate/wait-completion")
async def wait_for_completion(timeout_seconds: int = 30):
    """
    Espera completación de todas las transacciones pendientes
    """
    try:
        final_metrics = reconciliation_engine.wait_for_completion(timeout_seconds)
        
        return {
            "message": "Simulation completed" if final_metrics["pending_transactions"] == 0 else "Simulation timeout",
            "final_metrics": final_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to wait for completion: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
