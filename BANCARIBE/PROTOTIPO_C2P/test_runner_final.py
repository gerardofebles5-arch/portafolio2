# Test runner
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("BANCARIBE C2P TEST")
results = {"passed": 0, "failed": 0}

def test(name, fn):
    try:
        print(f"Testing {name}...", end=" ")
        fn()
        print("OK")
        results["passed"] += 1
    except Exception as e:
        print(f"FAIL: {e}")
        results["failed"] += 1

# Tests
def test1():
    from models.transaction import TransactionEvent, TransactionState
    from datetime import datetime
    e = TransactionEvent("1", "TX1", TransactionState.INITIATED, datetime.now(), {}, "")
    assert e.transaction_id == "TX1"

def test2():
    from src.retry_queue.retry_queue import RetryQueue
    q = RetryQueue()
    q.start()
    import time
    time.sleep(0.1)
    assert q.running
    q.stop()

test("Models", test1)
test("Queue", test2)
print(f"\nResults: {results['passed']} passed, {results['failed']} failed")
