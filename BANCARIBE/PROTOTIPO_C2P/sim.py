#!/usr/bin/env python3
import requests
import time
import random

API = "http://localhost:8000"
MERCHANTS = ["Amazon", "Walmart", "Farmatodo", "Cinepolis", "Supermercado", "Farmacia", "Gasolinera", "Restaurante"]

def create_transaction():
    data = {
        "qr_data": f"QR{random.randint(100000, 999999)}",
        "merchant_id": f"MERCH{random.randint(1, 10)}",
        "amount": round(random.uniform(10.00, 500.00), 2),
        "customer_id": f"CUST{random.randint(1, 100)}"
    }
    try:
        r = requests.post(f"{API}/transactions", json=data, timeout=5)
        result = r.json()
        tx_id = result.get("transaction_id", "N/A")
        status = result.get("status", "N/A")
        print(f"TX: {tx_id} | Status: {status} | Amount: ${data['amount']}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 60)
    print("SIMULADOR BANCARIBE C2P - GENERANDO TRANSACCIONES")
    print("=" * 60)
    
    count = 0
    while True:
        if create_transaction():
            count += 1
            if count % 10 == 0:
                print(f"Total: {count} transacciones enviadas")
        time.sleep(random.uniform(1.0, 3.0))

if __name__ == "__main__":
    main()
