"""
Event Store con SQLite para auditoría inmutable
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from ..models.transaction import TransactionEvent, TransactionState, TransactionSummary
except ImportError:
    from models.transaction import TransactionEvent, TransactionState, TransactionSummary


class EventStore:
    """
    Almacenamiento inmutable de eventos con SQLite
    Implementa patrón Event Sourcing para auditoría completa
    """
    
    def __init__(self, db_path: str = "data/c2p_events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        """
        Inicializa schema de base de datos
        """
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                metadata TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Índices para rendimiento
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transaction_id 
            ON events(transaction_id)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON events(timestamp)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_state 
            ON events(state)
        """)
        
        self.conn.commit()
    
    def append_event(self, event: TransactionEvent) -> bool:
        """
        Agrega evento inmutable al store
        """
        try:
            # Verificar integridad
            if not event.verify_signature():
                raise ValueError("Invalid event signature")
            
            self.conn.execute(
                """
                INSERT INTO events (id, transaction_id, state, timestamp, metadata, signature)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.transaction_id,
                    event.state.value,
                    int(event.timestamp.timestamp()),
                    json.dumps(event.metadata),
                    event.signature
                )
            )
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error appending event: {e}")
            self.conn.rollback()
            return False
    
    def get_current_state(self, transaction_id: str) -> Optional[TransactionEvent]:
        """
        Obtiene estado actual de una transacción
        """
        cursor = self.conn.execute(
            """
            SELECT * FROM events 
            WHERE transaction_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
            """,
            (transaction_id,)
        )
        
        row = cursor.fetchone()
        if row:
            return TransactionEvent(
                id=row["id"],
                transaction_id=row["transaction_id"],
                state=TransactionState(row["state"]),
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                metadata=json.loads(row["metadata"]),
                signature=row["signature"]
            )
        return None
    
    def get_transaction_history(self, transaction_id: str) -> List[TransactionEvent]:
        """
        Obtiene historial completo de una transacción
        """
        cursor = self.conn.execute(
            """
            SELECT * FROM events 
            WHERE transaction_id = ? 
            ORDER BY timestamp ASC
            """,
            (transaction_id,)
        )
        
        events = []
        for row in cursor.fetchall():
            events.append(TransactionEvent(
                id=row["id"],
                transaction_id=row["transaction_id"],
                state=TransactionState(row["state"]),
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                metadata=json.loads(row["metadata"]),
                signature=row["signature"]
            ))
        
        return events
    
    def get_transaction_summary(self, transaction_id: str) -> Optional[TransactionSummary]:
        """
        Genera resumen de transacción para dashboard
        """
        history = self.get_transaction_history(transaction_id)
        if not history:
            return None
        
        first_event = history[0]
        last_event = history[-1]
        
        # Calcular tiempo de procesamiento
        processing_time = int((last_event.timestamp - first_event.timestamp).total_seconds() * 1000)
        
        # Contar reintentos
        retry_count = len([e for e in history if e.state == TransactionState.FAILED])
        
        # Verificar si es duplicado
        is_duplicate = any(e.state == TransactionState.DUPLICATE_HANDLED for e in history)
        
        return TransactionSummary(
            transaction_id=transaction_id,
            current_state=last_event.state,
            merchant_id=first_event.metadata.get("merchant_id", ""),
            amount=first_event.metadata.get("amount", 0.0),
            created_at=first_event.timestamp,
            last_updated=last_event.timestamp,
            processing_time_ms=processing_time,
            retry_count=retry_count,
            is_duplicate=is_duplicate
        )
    
    def get_metrics(self, start_time: datetime = None, end_time: datetime = None) -> Dict[str, Any]:
        """
        Calcula métricas del sistema
        """
        if start_time is None:
            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time is None:
            end_time = datetime.now()
        
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        cursor = self.conn.execute("""
            SELECT 
                state,
                COUNT(*) as count,
                COUNT(DISTINCT transaction_id) as unique_transactions
            FROM events 
            WHERE timestamp BETWEEN ? AND ?
            AND state = (
                SELECT state FROM events e2 
                WHERE e2.transaction_id = events.transaction_id 
                ORDER BY timestamp DESC LIMIT 1
            )
            GROUP BY state
        """, (start_ts, end_ts))
        
        results = {}
        for row in cursor.fetchall():
            results[row["state"]] = row["count"]
        
        # Métricas adicionales
        total_transactions = results.get("unique_transactions", 0)
        completed = results.get("COMPLETED", 0)
        failed = results.get("FAILED", 0)
        
        success_rate = (completed / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_transactions": total_transactions,
            "completed": completed,
            "failed": failed,
            "processing": results.get("PROCESSING", 0),
            "initiated": results.get("INITIATED", 0),
            "success_rate": round(success_rate, 2),
            "failure_rate": round(100 - success_rate, 2)
        }
    
    def get_recent_transactions(self, limit: int = 10) -> List[TransactionSummary]:
        """
        Obtiene transacciones recientes para dashboard
        """
        cursor = self.conn.execute("""
            SELECT DISTINCT transaction_id 
            FROM events 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        summaries = []
        for row in cursor.fetchall():
            summary = self.get_transaction_summary(row["transaction_id"])
            if summary:
                summaries.append(summary)
        
        return summaries
    
    def close(self):
        """
        Cierra conexión a base de datos
        """
        if self.conn:
            self.conn.close()
