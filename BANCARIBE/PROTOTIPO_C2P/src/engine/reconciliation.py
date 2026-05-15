"""
Motor de Conciliación C2P - Corazón del sistema
"""

import uuid
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

try:
    from ..models.transaction import TransactionEvent, TransactionState, TransactionSummary
    from ..storage.event_store import EventStore
    from ..retry_queue.retry_queue import RetryQueue
except ImportError:
    from models.transaction import TransactionEvent, TransactionState, TransactionSummary
    from storage.event_store import EventStore
    from retry_queue.retry_queue import RetryQueue


@dataclass
class PaymentRequest:
    """Solicitud de pago P2P"""
    qr_data: str
    merchant_id: str
    amount: float
    customer_id: str
    reference: str = None
    
    def __post_init__(self):
        if not self.reference:
            self.reference = f"REF_{uuid.uuid4().hex[:8]}"


class C2PReconciliationEngine:
    """
    Motor central de conciliación de transacciones C2P
    Integra Event Store, Retry Queue y lógica de negocio
    """
    
    def __init__(self, event_store: EventStore, retry_queue: RetryQueue):
        self.event_store = event_store
        self.retry_queue = retry_queue
        self.pending_transactions = {}
        self.processed_count = 0
        self.failed_count = 0
        
        # Iniciar cola de reintentos
        self.retry_queue.start()
    
    def initiate_payment(self, payment_request: PaymentRequest) -> str:
        """
        Inicia una transacción de pago C2P
        """
        transaction_id = f"C2P_{uuid.uuid4().hex[:12].upper()}"
        
        # Crear evento inicial
        init_event = TransactionEvent(
            id=f"INIT_{transaction_id}",
            transaction_id=transaction_id,
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={
                "merchant_id": payment_request.merchant_id,
                "amount": payment_request.amount,
                "customer_id": payment_request.customer_id,
                "qr_data": payment_request.qr_data,
                "reference": payment_request.reference,
                "payment_type": "C2P"
            },
            signature=""  # Se generará automáticamente
        )
        
        # Guardar evento inicial
        if not self.event_store.append_event(init_event):
            raise Exception("Failed to initiate payment")
        
        # Registrar transacción pendiente
        self.pending_transactions[transaction_id] = {
            "payment_request": payment_request,
            "initiated_at": datetime.now(),
            "attempts": 0
        }
        
        # Iniciar procesamiento asíncrono
        self._process_payment_async(transaction_id)
        
        return transaction_id
    
    def _process_payment_async(self, transaction_id: str):
        """
        Procesa pago de forma asíncrona
        """
        payment_info = self.pending_transactions.get(transaction_id)
        if not payment_info:
            return
        
        payment_request = payment_info["payment_request"]
        payment_info["attempts"] += 1
        
        # Actualizar estado a PROCESSING
        self._update_state(transaction_id, TransactionState.PROCESSING, {
            "attempt": payment_info["attempts"],
            "processing_started": datetime.now().isoformat()
        }, signature="")
        
        # Simular procesamiento con el banco
        try:
            # Simular latencia de red (1-3 segundos)
            processing_time = random.uniform(1.0, 3.0)
            time.sleep(processing_time)
            
            # Simular成功率 (85% éxito, 15% fallo)
            if random.random() < 0.85:
                # Éxito
                self._complete_payment(transaction_id, processing_time)
            else:
                # Fallo
                self._fail_payment(transaction_id, "PROCESSING_ERROR", "Simulated processing error")
                
        except Exception as e:
            self._fail_payment(transaction_id, "SYSTEM_ERROR", str(e))
    
    def _complete_payment(self, transaction_id: str, processing_time: float):
        """
        Marca pago como completado
        """
        payment_info = self.pending_transactions.get(transaction_id)
        if not payment_info:
            return
        
        # Actualizar estado a COMPLETED
        self._update_state(transaction_id, TransactionState.COMPLETED, {
            "processing_time_ms": int(processing_time * 1000),
            "completed_at": datetime.now().isoformat(),
            "success": True
        })
        
        # Limpiar transacción pendiente
        del self.pending_transactions[transaction_id]
        self.processed_count += 1
        
        print(f"Payment completed: {transaction_id}")
    
    def _fail_payment(self, transaction_id: str, error_code: str, error_message: str):
        """
        Marca pago como fallido y agenda reintento
        """
        payment_info = self.pending_transactions.get(transaction_id)
        if not payment_info:
            return
        
        # Actualizar estado a FAILED
        self._update_state(transaction_id, TransactionState.FAILED, {
            "error_code": error_code,
            "error_message": error_message,
            "failed_at": datetime.now().isoformat(),
            "attempt": payment_info["attempts"]
        })
        
        # Agregar a cola de reintento
        self.retry_queue.enqueue_retry(
            transaction_id, 
            self._retry_payment,
            attempt=payment_info["attempts"]
        )
        
        self.failed_count += 1
        print(f"Payment failed: {transaction_id} - {error_message}")
    
    def _retry_payment(self, transaction_id: str, attempt: int) -> bool:
        """
        Callback para reintento de pago
        """
        payment_info = self.pending_transactions.get(transaction_id)
        if not payment_info:
            return False
        
        # Verificar si aún debemos reintentar
        if attempt >= self.retry_queue.max_retries:
            # Máximo de reintentos alcanzado
            self._update_state(transaction_id, TransactionState.FAILED, {
                "error_code": "MAX_RETRIES_EXCEEDED",
                "error_message": f"Maximum retries ({self.retry_queue.max_retries}) exceeded",
                "final_attempt": True
            })
            
            # Limpiar transacción pendiente
            del self.pending_transactions[transaction_id]
            return False
        
        # Reintentar procesamiento
        print(f"Retrying payment: {transaction_id} (attempt {attempt + 1})")
        self._process_payment_async(transaction_id)
        return True
    
    def _update_state(self, transaction_id: str, state: TransactionState, metadata: Dict[str, Any], signature: str = ""):
        """
        Actualiza estado de transacción
        """
        event = TransactionEvent(
            id=f"{state.value}_{transaction_id}_{int(time.time())}",
            transaction_id=transaction_id,
            state=state,
            timestamp=datetime.now(),
            metadata=metadata,
            signature=signature  # Se generará automáticamente si está vacío
        )
        
        self.event_store.append_event(event)
    
    def get_transaction_status(self, transaction_id: str) -> Optional[TransactionSummary]:
        """
        Obtiene estado actual de transacción
        """
        return self.event_store.get_transaction_summary(transaction_id)
    
    def get_recent_transactions(self, limit: int = 10) -> list:
        """
        Obtiene transacciones recientes
        """
        return self.event_store.get_recent_transactions(limit)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas del motor
        """
        # Métricas base del Event Store
        base_metrics = self.event_store.get_metrics()
        
        # Métricas adicionales del motor
        engine_metrics = {
            "pending_transactions": len(self.pending_transactions),
            "processed_by_engine": self.processed_count,
            "failed_by_engine": self.failed_count,
            "retry_queue_stats": self.retry_queue.get_stats()
        }
        
        # Combinar métricas
        combined_metrics = {**base_metrics, **engine_metrics}
        
        # Calcular tasa de éxito del motor
        total_engine = self.processed_count + self.failed_count
        if total_engine > 0:
            combined_metrics["engine_success_rate"] = (self.processed_count / total_engine) * 100
        else:
            combined_metrics["engine_success_rate"] = 0
        
        return combined_metrics
    
    def simulate_bulk_payments(self, count: int = 50) -> list:
        """
        Simula procesamiento masivo de pagos para testing
        """
        merchants = ["MERCHANT_001", "MERCHANT_002", "MERCHANT_003", "MERCHANT_004", "MERCHANT_005"]
        transaction_ids = []
        
        print(f"Simulating {count} bulk payments...")
        
        for i in range(count):
            payment_request = PaymentRequest(
                qr_data=f"QR_BULK_{i+1:03d}",
                merchant_id=random.choice(merchants),
                amount=round(random.uniform(10.0, 500.0), 2),
                customer_id=f"CUST_{random.randint(1, 1000):04d}"
            )
            
            transaction_id = self.initiate_payment(payment_request)
            transaction_ids.append(transaction_id)
            
            # Pequeña pausa entre transacciones
            time.sleep(0.1)
        
        print(f"{count} payments initiated")
        return transaction_ids
    
    def wait_for_completion(self, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Espera completación de todas las transacciones pendientes
        """
        start_time = time.time()
        
        while len(self.pending_transactions) > 0 and (time.time() - start_time) < timeout_seconds:
            time.sleep(1)
            print(f"Waiting for completion... {len(self.pending_transactions)} pending")
        
        metrics = self.get_metrics()
        
        if len(self.pending_transactions) == 0:
            print("All transactions completed")
        else:
            print(f"Timeout with {len(self.pending_transactions)} still pending")
        
        return metrics
    
    def shutdown(self):
        """
        Detiene el motor de conciliación
        """
        print("Shutting down reconciliation engine...")
        self.retry_queue.stop()
        print("Engine shutdown complete")
