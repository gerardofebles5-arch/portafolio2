"""
Tests para Retry Queue
"""

import pytest
import time
from unittest.mock import Mock

from src.retry_queue.retry_queue import RetryQueue, RetryItem


class TestRetryQueue:
    """Test suite para RetryQueue"""
    
    @pytest.fixture
    def retry_queue(self):
        """Fixture para RetryQueue"""
        queue = RetryQueue(max_retries=3, base_delay=0.1)  # Delay corto para tests
        yield queue
        queue.stop()
    
    def test_enqueue_retry_success(self, retry_queue):
        """Test agregar reintento exitosamente"""
        callback = Mock(return_value=True)
        
        result = retry_queue.enqueue_retry("TXN_001", callback)
        assert result is True
        assert retry_queue.queue.qsize() == 1
    
    def test_enqueue_retry_max_retries_exceeded(self, retry_queue):
        """Test rechazar reintento cuando se excede máximo"""
        callback = Mock()
        
        # Intentar agregar con máximo de reintentos excedido
        result = retry_queue.enqueue_retry("TXN_001", callback, attempt=5, max_retries=3)
        assert result is False
        assert retry_queue.queue.qsize() == 0
        assert retry_queue.failed_count == 1
    
    def test_retry_queue_processing_success(self, retry_queue):
        """Test procesamiento exitoso de reintento"""
        callback = Mock(return_value=True)
        
        # Agregar reintento
        retry_queue.enqueue_retry("TXN_001", callback, attempt=0)
        retry_queue.start()
        
        # Esperar procesamiento
        time.sleep(0.5)
        
        # Verificar callback fue llamado
        callback.assert_called_once_with("TXN_001", 0)
        assert retry_queue.processed_count == 1
        assert retry_queue.queue.qsize() == 0
    
    def test_retry_queue_processing_failure_retry(self, retry_queue):
        """Test reintento cuando callback falla"""
        callback = Mock(return_value=False)
        
        # Agregar reintento
        retry_queue.enqueue_retry("TXN_001", callback, attempt=0)
        retry_queue.start()
        
        # Esperar primer reintento fallido
        time.sleep(0.3)
        
        # Debe haberse agregado nuevo reintento
        assert retry_queue.retry_count >= 2
        assert callback.call_count >= 1
        
        # Esperar segundo reintento
        time.sleep(0.5)
        
        # Verificar múltiples llamadas
        assert callback.call_count >= 2
    
    def test_retry_queue_processing_exception(self, retry_queue):
        """Test manejo de excepción en callback"""
        callback = Mock(side_effect=Exception("Test error"))
        
        # Agregar reintento
        retry_queue.enqueue_retry("TXN_001", callback, attempt=0)
        retry_queue.start()
        
        # Esperar procesamiento
        time.sleep(0.5)
        
        # Debe haberse reintentado a pesar de la excepción
        assert retry_queue.retry_count >= 2
        assert callback.call_count >= 1
    
    def test_retry_queue_backoff_timing(self, retry_queue):
        """Test timing de backoff exponencial"""
        call_times = []
        
        def callback_with_timing(transaction_id, attempt):
            call_times.append(time.time())
            return attempt >= 2  # Éxito en tercer intento
        
        # Agregar reintento
        retry_queue.enqueue_retry("TXN_001", callback_with_timing, attempt=0)
        start_time = time.time()
        retry_queue.start()
        
        # Esperar todos los reintentos
        time.sleep(2.0)
        
        # Verificar timing entre llamadas
        assert len(call_times) >= 3
        
        # Primer reintento inmediato
        # Segundo reintento ~0.2s después (base_delay * 2^1)
        # Tercer reintento ~0.4s después (base_delay * 2^2)
        
        if len(call_times) >= 2:
            first_delay = call_times[1] - call_times[0]
            assert 0.15 <= first_delay <= 0.25  # ~0.2s
        
        if len(call_times) >= 3:
            second_delay = call_times[2] - call_times[1]
            assert 0.35 <= second_delay <= 0.45  # ~0.4s
    
    def test_retry_queue_stats(self, retry_queue):
        """Test estadísticas de la cola"""
        callback_success = Mock(return_value=True)
        callback_fail = Mock(return_value=False)
        
        # Agregar reintentos
        retry_queue.enqueue_retry("TXN_SUCCESS", callback_success)
        retry_queue.enqueue_retry("TXN_FAIL", callback_fail, attempt=2)  # Cerca del máximo
        
        retry_queue.start()
        time.sleep(0.5)
        
        stats = retry_queue.get_stats()
        assert stats["processed_count"] >= 1
        assert stats["retry_count"] >= 2
        assert stats["running"] is True
        assert 0 <= stats["success_rate"] <= 100
    
    def test_retry_queue_clear(self, retry_queue):
        """Test limpiar cola"""
        callback = Mock()
        
        # Agregar varios items
        retry_queue.enqueue_retry("TXN_001", callback)
        retry_queue.enqueue_retry("TXN_002", callback)
        retry_queue.enqueue_retry("TXN_003", callback)
        
        assert retry_queue.queue.qsize() == 3
        
        # Limpiar
        retry_queue.clear()
        
        assert retry_queue.queue.qsize() == 0
        assert retry_queue.processed_count == 0
        assert retry_queue.failed_count == 0
        assert retry_queue.retry_count == 0
    
    def test_retry_queue_start_stop(self, retry_queue):
        """Test iniciar y detener cola"""
        assert retry_queue.running is False
        
        retry_queue.start()
        assert retry_queue.running is True
        assert retry_queue.thread is not None
        
        retry_queue.stop()
        assert retry_queue.running is False
    
    def test_multiple_concurrent_retries(self, retry_queue):
        """Test múltiples reintentos concurrentes"""
        callbacks = []
        transaction_ids = []
        
        for i in range(5):
            tx_id = f"TXN_{i:03d}"
            callback = Mock(return_value=i < 3)  # Primeros 3 exitosos
            callbacks.append(callback)
            transaction_ids.append(tx_id)
            
            retry_queue.enqueue_retry(tx_id, callback, attempt=0)
        
        retry_queue.start()
        time.sleep(1.0)
        
        # Verificar callbacks llamados
        for i, callback in enumerate(callbacks):
            if i < 3:
                callback.assert_called_once()
            else:
                # Los últimos 2 deben tener reintentos
                assert callback.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
