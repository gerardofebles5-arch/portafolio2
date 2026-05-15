"""
Tests para modelos de datos
"""

import pytest
from datetime import datetime, timedelta

from src.models.transaction import TransactionEvent, TransactionState, TransactionSummary


class TestTransactionEvent:
    """Test suite para TransactionEvent"""
    
    def test_transaction_event_creation(self):
        """Test creación de evento de transacción"""
        timestamp = datetime.now()
        event = TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=timestamp,
            metadata={"merchant_id": "MERCHANT_001", "amount": 100.50}
        )
        
        assert event.id == "TEST_001"
        assert event.transaction_id == "TXN_001"
        assert event.state == TransactionState.INITIATED
        assert event.timestamp == timestamp
        assert event.metadata["merchant_id"] == "MERCHANT_001"
        assert event.metadata["amount"] == 100.50
        assert event.signature is not None  # Debe generarse automáticamente
    
    def test_transaction_event_auto_id(self):
        """Test generación automática de ID"""
        event = TransactionEvent(
            id="",  # ID vacío
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={"test": True}
        )
        
        assert event.id != ""  # Debe generarse automáticamente
        assert len(event.id) > 10  # UUID format
    
    def test_signature_calculation(self):
        """Test cálculo de firma digital"""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        event = TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=timestamp,
            metadata={"test": True}
        )
        
        # La firma debe ser consistente
        signature1 = event.signature
        signature2 = event._calculate_signature()
        assert signature1 == signature2
    
    def test_signature_verification(self):
        """Test verificación de firma"""
        event = TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=datetime.now(),
            metadata={"test": True}
        )
        
        # Firma válida debe pasar verificación
        assert event.verify_signature() is True
        
        # Firma inválida debe fallar
        event.signature = "INVALID_SIGNATURE"
        assert event.verify_signature() is False
    
    def test_to_dict(self):
        """Test conversión a diccionario"""
        timestamp = datetime.now()
        event = TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=timestamp,
            metadata={"merchant_id": "MERCHANT_001"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["id"] == "TEST_001"
        assert event_dict["transaction_id"] == "TXN_001"
        assert event_dict["state"] == "INITIATED"
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["metadata"]["merchant_id"] == "MERCHANT_001"
        assert event_dict["signature"] is not None
    
    def test_from_dict(self):
        """Test creación desde diccionario"""
        timestamp = datetime.now()
        original_event = TransactionEvent(
            id="TEST_001",
            transaction_id="TXN_001",
            state=TransactionState.INITIATED,
            timestamp=timestamp,
            metadata={"merchant_id": "MERCHANT_001"}
        )
        
        # Convertir a diccionario y recrear
        event_dict = original_event.to_dict()
        recreated_event = TransactionEvent.from_dict(event_dict)
        
        assert recreated_event.id == original_event.id
        assert recreated_event.transaction_id == original_event.transaction_id
        assert recreated_event.state == original_event.state
        assert recreated_event.timestamp == original_event.timestamp
        assert recreated_event.metadata == original_event.metadata
        assert recreated_event.signature == original_event.signature
    
    def test_all_transaction_states(self):
        """Test todos los estados de transacción"""
        timestamp = datetime.now()
        
        for state in TransactionState:
            event = TransactionEvent(
                id=f"TEST_{state.value}",
                transaction_id="TXN_001",
                state=state,
                timestamp=timestamp,
                metadata={"test": True}
            )
            
            assert event.state == state
            assert event.verify_signature() is True


class TestTransactionSummary:
    """Test suite para TransactionSummary"""
    
    def test_transaction_summary_creation(self):
        """Test creación de resumen de transacción"""
        created_at = datetime.now()
        last_updated = created_at + timedelta(seconds=5)
        
        summary = TransactionSummary(
            transaction_id="TXN_001",
            current_state=TransactionState.COMPLETED,
            merchant_id="MERCHANT_001",
            amount=100.50,
            created_at=created_at,
            last_updated=last_updated,
            processing_time_ms=5000,
            retry_count=2,
            is_duplicate=False
        )
        
        assert summary.transaction_id == "TXN_001"
        assert summary.current_state == TransactionState.COMPLETED
        assert summary.merchant_id == "MERCHANT_001"
        assert summary.amount == 100.50
        assert summary.created_at == created_at
        assert summary.last_updated == last_updated
        assert summary.processing_time_ms == 5000
        assert summary.retry_count == 2
        assert summary.is_duplicate is False
    
    def test_transaction_summary_to_dict(self):
        """Test conversión a diccionario"""
        created_at = datetime.now()
        last_updated = created_at + timedelta(seconds=5)
        
        summary = TransactionSummary(
            transaction_id="TXN_001",
            current_state=TransactionState.COMPLETED,
            merchant_id="MERCHANT_001",
            amount=100.50,
            created_at=created_at,
            last_updated=last_updated,
            processing_time_ms=5000,
            retry_count=2,
            is_duplicate=False
        )
        
        summary_dict = summary.to_dict()
        
        assert summary_dict["transaction_id"] == "TXN_001"
        assert summary_dict["current_state"] == "COMPLETED"
        assert summary_dict["merchant_id"] == "MERCHANT_001"
        assert summary_dict["amount"] == 100.50
        assert summary_dict["created_at"] == created_at.isoformat()
        assert summary_dict["last_updated"] == last_updated.isoformat()
        assert summary_dict["processing_time_ms"] == 5000
        assert summary_dict["retry_count"] == 2
        assert summary_dict["is_duplicate"] is False
    
    def test_transaction_summary_default_values(self):
        """Test valores por defecto"""
        created_at = datetime.now()
        
        summary = TransactionSummary(
            transaction_id="TXN_001",
            current_state=TransactionState.COMPLETED,
            merchant_id="MERCHANT_001",
            amount=100.50,
            created_at=created_at,
            last_updated=created_at,
            processing_time_ms=1000,
            retry_count=0
        )
        
        # is_duplicate debe ser False por defecto
        assert summary.is_duplicate is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
