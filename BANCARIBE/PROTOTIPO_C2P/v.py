#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("BANCARIBE C2P TEST")
p = f = 0

def test(n, fn):
    global p, f
    try:
        print(f"[TEST] {n}...", end=" ")
        fn()
        print("OK")
        p += 1
    except Exception as e:
        print(f"FAIL: {e}")
        f += 1

def t1():
    from models.transaction import TransactionEvent, TransactionState
    from datetime import datetime
    e = TransactionEvent("1", "TX1", TransactionState.INITIATED, datetime.now(), {}, "")
    assert e.transaction_id == "TX1"

def t2():
    from src.retry_queue.retry_queue import RetryQueue
    q = RetryQueue()
    q.start()
    import time
    time.sleep(0.2)
    assert q.running
    q.stop()

test("Models", t1)
test("Queue", t2)
print(f"\nResults: {p} passed, {f} failed")
