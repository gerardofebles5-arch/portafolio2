#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("BANCARIBE C2P - BASIC TEST")
print("=" * 40)

passed = 0
failed = 0

try:
    from models.transaction import TransactionEvent, TransactionState
    print("[OK] Models")
    passed += 1
except Exception as e:
    print(f"[FAIL] Models: {e}")
    failed += 1

try:
    from src.retry_queue.retry_queue import RetryQueue
    print("[OK] Queue")
    passed += 1
except Exception as e:
    print(f"[FAIL] Queue: {e}")
    failed += 1

print("=" * 40)
print(f"Results: {passed} passed, {failed} failed")
