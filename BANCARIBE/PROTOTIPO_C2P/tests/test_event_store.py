"""
Tests para Event Store
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.models.transaction import TransactionEvent, TransactionState
from src.storage.event_store import EventStore


class TestEventStore:
    """Test suite para EventStore"""
    
    @pytest.fixture
    def event_store(self):
        """Fixture para EventStore con base de datos temporal"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        store = EventStore(temp_db.name)
        yield store
        
        store.close()
        os.unlink(temp_db.name)
    
    @pytest.fixture
    def sample_event(self):
        """Fixture para evento de muestra"""
        return TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_TEST_001",
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={
                "merchant_id": "MERCHANT_001",
                "amount": 100.50,
                "test": True
            }
        )
    
    def test_append_event_success(self, event_store, sample_event):
        """Test agregar evento exitosamente"""
        result = event_store.append_event(sample_event)
        assert result is True
        
        # Verificar que se guardó
        current = event_store.get_current_state(sample_event.transaction_id)
        assert current is not None
        assert current.transaction_id == sample_event.transaction_id
        assert current.state == TransactionState.INITIATED
    
    def test_append_event_invalid_signature(self, event_store):
        """Test rechazar evento con firma inválida"""
        invalid_event = TransactionEvent(
            id="TEST_002",
            transaction_id="TXN_TEST_002",
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={"test": True},
            signature="INVALID_SIGNATURE"
        )
        
        result = event_store.append_event(invalid_event)
        assert result is False
    
    def test_get_current_state_not_found(self, event_store):
        """Test obtener estado de transacción inexistente"""
        result = event_store.get_current_state("NON_EXISTENT")
        assert result is None
    
    def test_get_transaction_history(self, event_store, sample_event):
        """Test obtener historial completo"""
        # Agregar múltiples eventos
        event_store.append_event(sample_event)
        
        # Evento de procesamiento
        process_event = TransactionEvent(
            id="TEST_002",
            transaction_id=sample_event.transaction_id,
            state=TransactionState.PROCESSING,
            timestamp=datetime.now() + timedelta(seconds=1),
            metadata={"processing": True}
        )
        event_store.append_event(process_event)
        
        # Evento completado
        complete_event = TransactionEvent(
            id="TEST_003",
            transaction_id=sample_event.transaction_id,
            state=TransactionState.COMPLETED,
            timestamp=datetime.now() + timedelta(seconds=2),
            metadata={"completed": True}
        )
        event_store.append_event(complete_event)
        
        # Obtener historial
        history = event_store.get_transaction_history(sample_event.transaction_id)
        assert len(history) == 3
        assert history[0].state == TransactionState.INITIATED
        assert history[1].state == TransactionState.PROCESSING
        assert history[2].state == TransactionState.COMPLETED
    
    def test_get_transaction_summary(self, event_store, sample_event):
        """Test obtener resumen de transacción"""
        # Agregar evento inicial
        event_store.append_event(sample_event)
        
        # Agregar evento completado
        complete_event = TransactionEvent(
            id="TEST_004",
            transaction_id=sample_event.transaction_id,
            state=TransactionState.COMPLETED,
            timestamp=datetime.now() + timedelta(seconds=5),
            metadata={"completed": True}
        )
        event_store.append_event(complete_event)
        
        # Obtener resumen
        summary = event_store.get_transaction_summary(sample_event.transaction_id)
        assert summary is not None
        assert summary.transaction_id == sample_event.transaction_id
        assert summary.current_state == TransactionState.COMPLETED
        assert summary.merchant_id == "MERCHANT_001"
        assert summary.amount == 100.50
        assert summary.processing_time_ms > 0
        assert summary.retry_count == 0
        assert summary.is_duplicate is False
    
    def test_get_metrics_empty(self, event_store):
        """Test obtener métricas con base de datos vacía"""
        metrics = event_store.get_metrics()
        assert metrics["total_transactions"] == 0
        assert metrics["completed"] == 0
        assert metrics["failed"] == 0
        assert metrics["success_rate"] == 0
    
    def test_get_metrics_with_data(self, event_store, sample_event):
        """Test obtener métricas con datos"""
        # Agregar transacción completada
        event_store.append_event(sample_event)
        
        complete_event = TransactionEvent(
            id="TEST_005",
            transaction_id=sample_event.transaction_id,
            state=TransactionState.COMPLETED,
            timestamp=datetime.now() + timedelta(seconds=1),
            metadata={"completed": True}
        )
        event_store.append_event(complete_event)
        
        # Agregar transacción fallida
        failed_event = TransactionEvent(
            id="TEST_006",
            transaction_id="TXN_FAILED",
            state=TransactionState.FAILED,
            timestamp=datetime.now(),
            metadata={"error": "test error"}
        )
        event_store.append_event(failed_event)
        
        # Obtener métricas
        metrics = event_store.get_metrics()
        assert metrics["total_transactions"] == 2
        assert metrics["completed"] == 1
        assert metrics["failed"] == 1
        assert metrics["success_rate"] == 50.0
        assert metrics["failure_rate"] == 50.0
    
    def test_get_recent_transactions(self, event_store):
        """Test obtener transacciones recientes"""
        # Crear múltiples transacciones
        for i in range(5):
            event = TransactionEvent(
                id=f"TEST_{i}",
                transaction_id=f"TXN_{i}",
                state=TransactionState.COMPLETED,
                timestamp=datetime.now() + timedelta(seconds=i),
                metadata={"index": i}
            )
            event_store.append_event(event)
        
        # Obtener transacciones recientes
        recent = event_store.get_recent_transactions(limit=3)
        assert len(recent) == 3
        
        # Deben estar en orden descendente por timestamp
        assert recent[0].transaction_id == "TXN_4"
        assert recent[1].transaction_id == "TXN_3"
        assert recent[2].transaction_id == "TXN_2"
    
    def test_duplicate_transaction_handling(self, event_store):
        """Test manejo de transacciones duplicadas"""
        # Primera transacción
        event1 = TransactionEvent(
            id="TEST_DUP_1",
            transaction_id="TXN_DUPLICATE",
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={"merchant_id": "MERCHANT_001", "amount": 100.0}
        )
        event_store.append_event(event1)
        
        # Segunda transacción con mismos datos (posible duplicado)
        event2 = TransactionEvent(
            id="TEST_DUP_2",
            transaction_id="TXN_DUPLICATE_2",
            state=TransactionState.INITIATED,
            timestamp=datetime.now() + timedelta(seconds=1),
            metadata={"merchant_id": "MERCHANT_001", "amount": 100.0}
        )
        event_store.append_event(event2)
        
        # Marcar como duplicado
        duplicate_event = TransactionEvent(
            id="TEST_DUP_3",
            transaction_id="TXN_DUPLICATE_2",
            state=TransactionState.DUPLICATE_HANDLED,
            timestamp=datetime.now() + timedelta(seconds=2),
            metadata={"original_transaction": "TXN_DUPLICATE"}
        )
        event_store.append_event(duplicate_event)
        
        # Verificar resumen detecta duplicado
        summary = event_store.get_transaction_summary("TXN_DUPLICATE_2")
        assert summary is not None
        assert summary.is_duplicate is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
