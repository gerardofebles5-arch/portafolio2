#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing MVP BANCARIBE C2P...")
print("-" * 50)

try:
    from models.transaction import TransactionEvent, TransactionState
    print("Models OK")
except Exception as e:
    print(f"Models error: {e}")
    sys.exit(1)

try:
    from storage.event_store import EventStore
    print("EventStore OK")
except Exception as e:
    print(f"EventStore error: {e}")

try:
    from src.retry_queue.retry_queue import RetryQueue
    print("RetryQueue OK")
except Exception as e:
    print(f"RetryQueue error: {e}")

try:
    from engine.reconciliation import C2PReconciliationEngine, PaymentRequest
    print("Engine OK")
except Exception as e:
    print(f"Engine error: {e}")

print("-" * 50)
print("Basic tests completed!")
