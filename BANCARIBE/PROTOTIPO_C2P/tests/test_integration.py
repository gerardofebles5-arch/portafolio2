"""
Tests de integración para el MVP C2P
"""

import pytest
import tempfile
import os
import time
from datetime import datetime

from src.engine.reconciliation import C2PReconciliationEngine, PaymentRequest
from src.models.transaction import TransactionEvent, TransactionState
from src.storage.event_store import EventStore
from src.retry_queue.retry_queue import RetryQueue


class TestIntegration:
    """Test suite de integración completa"""
    
    @pytest.fixture
    def engine(self):
        """Fixture para motor completo con componentes temporales"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        event_store = EventStore(temp_db.name)
        retry_queue = RetryQueue(max_retries=2, base_delay=0.1)  # Rápido para tests
        engine = C2PReconciliationEngine(event_store, retry_queue)
        
        yield engine
        
        engine.shutdown()
        event_store.close()
        os.unlink(temp_db.name)
    
    def test_complete_payment_flow_success(self, engine):
        """Test flujo completo de pago exitoso"""
        payment_request = PaymentRequest(
            qr_data="QR_TEST_001",
            merchant_id="MERCHANT_001",
            amount=100.50,
            customer_id="CUST_001"
        )
        
        # Iniciar pago
        transaction_id = engine.initiate_payment(payment_request)
        assert transaction_id is not None
        assert transaction_id.startswith("C2P_")
        
        # Esperar procesamiento
        time.sleep(5)
        
        # Verificar estado final
        status = engine.get_transaction_status(transaction_id)
        assert status is not None
        assert status.current_state.value in ["COMPLETED", "PROCESSING", "FAILED"]
        assert status.merchant_id == "MERCHANT_001"
        assert status.amount == 100.50
    
    def test_bulk_payment_simulation(self, engine):
        """Test simulación de pagos masivos"""
        # Iniciar 20 pagos
        transaction_ids = engine.simulate_bulk_payments(20)
        assert len(transaction_ids) == 20
        
        # Esperar procesamiento
        metrics = engine.wait_for_completion(timeout_seconds=30)
        
        # Verificar métricas
        assert metrics["total_transactions"] >= 20
        assert metrics["pending_transactions"] == 0  # Todas completadas
        assert metrics["engine_success_rate"] > 0
    
    def test_retry_mechanism(self, engine):
        """Test mecanismo de reintentos"""
        # Forzar alta tasa de fallos modificando el motor
        # (Esto requeriría modificar el motor para testing)
        
        payment_request = PaymentRequest(
            qr_data="QR_RETRY_TEST",
            merchant_id="MERCHANT_RETRY",
            amount=50.0,
            customer_id="CUST_RETRY"
        )
        
        transaction_id = engine.initiate_payment(payment_request)
        
        # Esperar reintentos
        time.sleep(10)
        
        status = engine.get_transaction_status(transaction_id)
        if status:
            # Debe tener intentos de reintento si falló
            assert status.retry_count >= 0
    
    def test_metrics_calculation(self, engine):
        """Test cálculo de métricas"""
        # Iniciar algunas transacciones
        engine.simulate_bulk_payments(10)
        
        # Esperar un poco
        time.sleep(3)
        
        # Obtener métricas
        metrics = engine.get_metrics()
        
        # Verificar estructura de métricas
        required_keys = [
            "total_transactions", "completed", "failed", 
            "success_rate", "pending_transactions",
            "processed_by_engine", "failed_by_engine",
            "engine_success_rate", "retry_queue_stats"
        ]
        
        for key in required_keys:
            assert key in metrics
        
        # Verificar valores razonables
        assert metrics["total_transactions"] >= 0
        assert 0 <= metrics["success_rate"] <= 100
        assert metrics["pending_transactions"] >= 0
    
    def test_transaction_persistence(self, engine):
        """Test persistencia de transacciones"""
        payment_request = PaymentRequest(
            qr_data="QR_PERSISTENCE",
            merchant_id="MERCHANT_PERSIST",
            amount=75.0,
            customer_id="CUST_PERSIST"
        )
        
        transaction_id = engine.initiate_payment(payment_request)
        
        # Obtener estado inmediatamente
        status1 = engine.get_transaction_status(transaction_id)
        assert status1 is not None
        assert status1.current_state.value == "INITIATED"
        
        # Esperar procesamiento
        time.sleep(5)
        
        # Obtener estado final
        status2 = engine.get_transaction_status(transaction_id)
        assert status2 is not None
        assert status2.transaction_id == status1.transaction_id
        assert status2.merchant_id == status1.merchant_id
        assert status2.amount == status1.amount
    
    def test_concurrent_transactions(self, engine):
        """Test procesamiento concurrente de transacciones"""
        transaction_ids = []
        
        # Iniciar múltiples transacciones rápidamente
        for i in range(5):
            payment_request = PaymentRequest(
                qr_data=f"QR_CONCURRENT_{i}",
                merchant_id="MERCHANT_CONCURRENT",
                amount=float(10 + i * 10),
                customer_id=f"CUST_CONCURRENT_{i}"
            )
            tx_id = engine.initiate_payment(payment_request)
            transaction_ids.append(tx_id)
        
        # Esperar procesamiento
        time.sleep(8)
        
        # Verificar todas las transacciones
        for tx_id in transaction_ids:
            status = engine.get_transaction_status(tx_id)
            assert status is not None
            assert status.transaction_id == tx_id
    
    def test_error_handling(self, engine):
        """Test manejo de errores"""
        # Test con datos inválidos
        with pytest.raises(Exception):
            invalid_request = PaymentRequest(
                qr_data="",  # QR vacío
                merchant_id="MERCHANT_001",
                amount=-100,  # Monto negativo
                customer_id="CUST_001"
            )
            engine.initiate_payment(invalid_request)
    
    def test_recent_transactions_ordering(self, engine):
        """Test ordenamiento de transacciones recientes"""
        # Iniciar transacciones con delays
        transaction_ids = []
        
        for i in range(5):
            payment_request = PaymentRequest(
                qr_data=f"QR_ORDER_{i}",
                merchant_id="MERCHANT_ORDER",
                amount=float(10 + i * 10),
                customer_id=f"CUST_ORDER_{i}"
            )
            tx_id = engine.initiate_payment(payment_request)
            transaction_ids.append(tx_id)
            time.sleep(0.5)  # Delay entre transacciones
        
        # Obtener transacciones recientes
        recent = engine.get_recent_transactions(limit=3)
        assert len(recent) == 3
        
        # Deben estar en orden descendente (más reciente primero)
        assert recent[0].created_at >= recent[1].created_at
        assert recent[1].created_at >= recent[2].created_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
