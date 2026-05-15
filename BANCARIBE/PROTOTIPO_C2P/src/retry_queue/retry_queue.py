"""
Retry Queue con backoff exponencial para manejo de fallos
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional
from datetime import datetime
import uuid
import heapq


@dataclass(order=True)
class RetryItem:
    """
    Item de cola para reintento con prioridad por tiempo
    """
    retry_time: float
    transaction_id: str = field(compare=False)
    attempt: int = field(compare=False)
    callback: Callable = field(compare=False)
    max_retries: int = field(compare=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)


class RetryQueue:
    """
    Cola de reintentos con backoff exponencial
    Maneja fallos de transacciones con reintentos automáticos
    """
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.queue = []  # Usar lista con heapq
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
    
    def enqueue_retry(self, 
                     transaction_id: str, 
                     callback: Callable, 
                     attempt: int = 0,
                     max_retries: Optional[int] = None) -> bool:
        """
        Agrega transacción a cola de reintento
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        if attempt >= max_retries:
            print(f"Max retries exceeded for {transaction_id}")
            self.failed_count += 1
            return False
        
        # Calcular delay con backoff exponencial
        delay = self.base_delay * (2 ** attempt)
        retry_time = time.time() + delay
        
        item = RetryItem(
            retry_time=retry_time,
            transaction_id=transaction_id,
            attempt=attempt,
            callback=callback,
            max_retries=max_retries
        )
        
        with self.lock:
            heapq.heappush(self.queue, item)
        
        self.retry_count += 1
        
        print(f"Retry {attempt} queued for {transaction_id} in {delay:.1f}s")
        return True
    
    def _process_retries(self):
        """
        Procesa reintentos en background
        """
        while self.running:
            try:
                with self.lock:
                    if self.queue:
                        item = heapq.heappop(self.queue)
                    else:
                        item = None
                
                if item:
                    if time.time() >= item.retry_time:
                        # Es tiempo de procesar
                        print(f"Processing retry {item.attempt} for {item.transaction_id}")
                        
                        try:
                            # Ejecutar callback
                            success = item.callback(item.transaction_id, item.attempt)
                            
                            if success:
                                self.processed_count += 1
                                print(f"Retry successful for {item.transaction_id}")
                            else:
                                # Re-queue con siguiente intento
                                self.enqueue_retry(
                                    item.transaction_id,
                                    item.callback,
                                    item.attempt + 1,
                                    item.max_retries
                                )
                                
                        except Exception as e:
                            print(f"Retry callback failed for {item.transaction_id}: {e}")
                            # Re-queue con siguiente intento
                            self.enqueue_retry(
                                item.transaction_id,
                                item.callback,
                                item.attempt + 1,
                                item.max_retries
                            )
                    else:
                        # Todavía no es tiempo, volver a la cola
                        with self.lock:
                            heapq.heappush(self.queue, item)
                else:
                    # No hay items en la cola
                    pass
                
                time.sleep(0.1)  # Pequeña pausa para no consumir CPU
                
            except Exception as e:
                print(f"Error in retry queue processing: {e}")
                time.sleep(1.0)  # Espera más larga en caso de error
    
    def start(self):
        """
        Inicia procesamiento de reintentos en background
        """
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_retries, daemon=True)
        self.thread.start()
        print("Retry queue started")
    
    def stop(self):
        """
        Detiene procesamiento de reintentos
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        print("Retry queue stopped")
    
    def get_stats(self) -> dict:
        """
        Obtiene estadísticas de la cola
        """
        with self.lock:
            queue_size = len(self.queue)
        
        return {
            "queue_size": queue_size,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "retry_count": self.retry_count,
            "success_rate": (self.processed_count / max(1, self.processed_count + self.failed_count)) * 100,
            "running": self.running
        }
    
    def clear(self):
        """
        Limpia la cola (para testing)
        """
        with self.lock:
            self.queue.clear()
        
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
