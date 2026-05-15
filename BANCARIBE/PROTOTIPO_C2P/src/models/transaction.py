"""
Modelos de transacciones y eventos para el sistema C2P
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any
import uuid
import hashlib
import hmac


class TransactionState(Enum):
    """Estados posibles de una transacción"""
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    DUPLICATE_HANDLED = "DUPLICATE_HANDLED"


@dataclass
class TransactionEvent:
    """
    Evento inmutable de transacción para event sourcing
    Cada cambio de estado genera un nuevo evento
    """
    id: str
    transaction_id: str
    state: TransactionState
    timestamp: datetime
    metadata: Dict[str, Any]
    signature: str  # Firma digital para integridad
    
    def __post_init__(self):
        """Validación post-creación"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.signature:
            self.signature = self._calculate_signature()
    
    def _calculate_signature(self) -> str:
        """
        Calcula firma digital HMAC-SHA256 para integridad
        """
        message = f"{self.transaction_id}{self.state.value}{self.timestamp.isoformat()}"
        return hmac.new(
            b"bancaribe_c2p_secret_key_2025", 
            message.encode(), 
            hashlib.sha256
        ).hexdigest()
    
    def verify_signature(self) -> bool:
        """
        Verifica la integridad del evento
        """
        expected_signature = self._calculate_signature()
        return hmac.compare_digest(self.signature, expected_signature)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para serialización
        """
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "state": self.state.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransactionEvent":
        """
        Crea evento desde diccionario
        """
        return cls(
            id=data["id"],
            transaction_id=data["transaction_id"],
            state=TransactionState(data["state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data["metadata"],
            signature=data["signature"]
        )


@dataclass
class TransactionSummary:
    """
    Resumen de transacción para dashboard
    """
    transaction_id: str
    current_state: TransactionState
    merchant_id: str
    amount: float
    created_at: datetime
    last_updated: datetime
    processing_time_ms: int
    retry_count: int
    is_duplicate: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte a diccionario para API
        """
        return {
            "transaction_id": self.transaction_id,
            "current_state": self.current_state.value,
            "merchant_id": self.merchant_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "processing_time_ms": self.processing_time_ms,
            "retry_count": self.retry_count,
            "is_duplicate": self.is_duplicate
        }
