#!/usr/bin/env python3
"""
Generador de datos de muestra para testing
"""

import sys
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.transaction import TransactionEvent, TransactionState
from storage.event_store import EventStore


def generate_sample_transactions(count: int = 100):
    """
    Genera transacciones de muestra
    """
    merchants = ["MERCHANT_001", "MERCHANT_002", "MERCHANT_003", "MERCHANT_004", "MERCHANT_005"]
    
    events = []
    current_time = datetime.now()
    
    for i in range(count):
        transaction_id = f"TXN_{i+1:06d}"
        merchant_id = random.choice(merchants)
        amount = round(random.uniform(10.0, 500.0), 2)
        
        # Tiempo aleatorio en últimas 24 horas
        created_at = current_time - timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        
        # Evento inicial
        init_event = TransactionEvent(
            id=f"INIT_{transaction_id}",
            transaction_id=transaction_id,
            state=TransactionState.INITIATED,
            timestamp=created_at,
            metadata={
                "merchant_id": merchant_id,
                "amount": amount,
                "qr_data": f"QR_{transaction_id}",
                "customer_id": f"CUST_{random.randint(1, 1000):04d}"
            }
        )
        events.append(init_event)
        
        # Simular procesamiento (80% éxito, 20% fallo)
        if random.random() < 0.8:
            # Éxito
            processing_time = random.randint(1, 5)
            process_time = created_at + timedelta(seconds=processing_time)
            
            process_event = TransactionEvent(
                id=f"PROC_{transaction_id}",
                transaction_id=transaction_id,
                state=TransactionState.PROCESSING,
                timestamp=process_time,
                metadata={"processing_time_ms": processing_time * 1000}
            )
            events.append(process_event)
            
            # Completado
            complete_time = process_time + timedelta(seconds=random.randint(1, 3))
            complete_event = TransactionEvent(
                id=f"COMP_{transaction_id}",
                transaction_id=transaction_id,
                state=TransactionState.COMPLETED,
                timestamp=complete_time,
                metadata={
                    "completion_time_ms": (complete_time - created_at).total_seconds() * 1000,
                    "reference_number": f"REF_{transaction_id}"
                }
            )
            events.append(complete_event)
            
        else:
            # Fallo con reintento
            processing_time = random.randint(1, 5)
            process_time = created_at + timedelta(seconds=processing_time)
            
            process_event = TransactionEvent(
                id=f"PROC_{transaction_id}",
                transaction_id=transaction_id,
                state=TransactionState.PROCESSING,
                timestamp=process_time,
                metadata={"processing_time_ms": processing_time * 1000}
            )
            events.append(process_event)
            
            # Fallo
            fail_time = process_time + timedelta(seconds=random.randint(2, 10))
            fail_event = TransactionEvent(
                id=f"FAIL_{transaction_id}",
                transaction_id=transaction_id,
                state=TransactionState.FAILED,
                timestamp=fail_time,
                metadata={
                    "error_code": "TIMEOUT",
                    "error_message": "Network timeout during processing"
                }
            )
            events.append(fail_event)
            
            # Reintento exitoso (50% de los fallos)
            if random.random() < 0.5:
                retry_time = fail_time + timedelta(seconds=random.randint(5, 15))
                retry_event = TransactionEvent(
                    id=f"RETRY_{transaction_id}",
                    transaction_id=transaction_id,
                    state=TransactionState.PROCESSING,
                    timestamp=retry_time,
                    metadata={"retry_attempt": 1}
                )
                events.append(retry_event)
                
                # Éxito después de reintento
                success_time = retry_time + timedelta(seconds=random.randint(2, 5))
                success_event = TransactionEvent(
                    id=f"SUCCESS_{transaction_id}",
                    transaction_id=transaction_id,
                    state=TransactionState.COMPLETED,
                    timestamp=success_time,
                    metadata={
                        "retry_success": True,
                        "total_processing_time_ms": (success_time - created_at).total_seconds() * 1000
                    }
                )
                events.append(success_event)
    
    return events


def main():
    """
    Función principal
    """
    print("🔄 Generando datos de muestra...")
    
    # Crear directorio data si no existe
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generar eventos
    events = generate_sample_transactions(100)
    print(f"✅ Generados {len(events)} eventos")
    
    # Guardar en EventStore
    store = EventStore()
    
    success_count = 0
    for event in events:
        if store.append_event(event):
            success_count += 1
    
    print(f"✅ Guardados {success_count} eventos en la base de datos")
    
    # Generar métricas
    metrics = store.get_metrics()
    print(f"📊 Métricas generadas:")
    print(f"   - Total transacciones: {metrics['total_transactions']}")
    print(f"   - Completadas: {metrics['completed']}")
    print(f"   - Fallidas: {metrics['failed']}")
    print(f"   - Tasa éxito: {metrics['success_rate']}%")
    
    # Guardar métricas en archivo JSON
    with open(data_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"💾 Métricas guardadas en {data_dir / 'metrics.json'}")
    
    store.close()
    print("🎉 Datos de muestra generados exitosamente")


if __name__ == "__main__":
    main()
