// API URL - Cambiar a la URL de producción cuando esté online
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : window.location.origin.replace(':8081', '') + ':8000';

// Login functionality
function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // Simulación de autenticación
    if (username && password) {
        // Guardar sesión
        localStorage.setItem('user', JSON.stringify({
            username: username,
            name: 'Juan Pérez',
            phone: '0414-123-4567'
        }));
        
        // Mostrar app principal
        document.getElementById('loginScreen').style.display = 'none';
        document.getElementById('mainApp').style.display = 'block';
        
        // Cargar datos
        loadTransactions();
    }
}

function handleLogout() {
    localStorage.removeItem('user');
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
    closeMenu();
}

// Menu functionality
function showMenu() {
    document.getElementById('sideMenu').classList.add('active');
}

function closeMenu() {
    document.getElementById('sideMenu').classList.remove('active');
}

function showSection(section) {
    closeMenu();
    switch(section) {
        case 'home':
            // Already on home
            break;
        case 'transfers':
            showTransfer();
            break;
        case 'recharge':
            showRecharge();
            break;
        case 'cards':
            document.getElementById('cardsModal').classList.add('active');
            break;
        case 'history':
            document.getElementById('historyModal').classList.add('active');
            break;
        case 'profile':
            document.getElementById('profileModal').classList.add('active');
            break;
        case 'support':
            document.getElementById('supportModal').classList.add('active');
            break;
        default:
            alert(`Sección: ${section} - En desarrollo`);
    }
}

// Modal functions
function showQRScanner() {
    document.getElementById('qrModal').classList.add('active');
}

function showPayment() {
    document.getElementById('paymentModal').classList.add('active');
}

function showTransfer() {
    document.getElementById('transferModal').classList.add('active');
}

function showRecharge() {
    document.getElementById('rechargeModal').classList.add('active');
}

function showHistory() {
    alert('Función de historial en desarrollo');
}

function closeModal() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

// Simulate QR scan
function simulateScan() {
    const qrData = 'QR' + Math.random().toString(36).substring(7);
    console.log('QR escaneado:', qrData);
    
    // Show payment modal with QR data
    closeModal();
    showPayment();
    
    // Pre-fill payment form
    const amountInput = document.querySelector('.payment-form input[type="number"]');
    if (amountInput) {
        amountInput.value = (Math.random() * 500 + 10).toFixed(2);
    }
}

// Process transfer
async function processTransfer() {
    const amountInput = document.querySelector('#transferModal input[type="number"]');
    const recipientInput = document.querySelector('#transferModal input[type="text"]');
    
    const amount = parseFloat(amountInput?.value) || 0;
    const recipient = recipientInput?.value || '';
    
    if (amount <= 0) {
        alert('Por favor ingrese un monto válido');
        return;
    }
    
    if (!recipient) {
        alert('Por favor ingrese el destinatario');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                qr_data: 'TRANSFER_' + recipient,
                merchant_id: 'TRANSFER',
                amount: amount,
                customer_id: recipient,
                reference: 'P2P_TRANSFER'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Transferencia exitosa!\nID: ${result.transaction_id}`);
            closeModal();
            loadTransactions();
        } else {
            alert('Error al procesar transferencia: ' + result.detail);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión con el servidor');
    }
}

// Process recharge
async function processRecharge() {
    const amountInput = document.querySelector('#rechargeModal input[type="number"]');
    const numberInput = document.querySelector('#rechargeModal input[type="text"]');
    
    const amount = parseFloat(amountInput?.value) || 0;
    const number = numberInput?.value || '';
    
    if (amount <= 0) {
        alert('Por favor ingrese un monto válido');
        return;
    }
    
    if (!number) {
        alert('Por favor ingrese el número');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                qr_data: 'RECHARGE_' + number,
                merchant_id: 'RECHARGE',
                amount: amount,
                customer_id: number,
                reference: 'MOBILE_RECHARGE'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Recarga exitosa!\nID: ${result.transaction_id}`);
            closeModal();
            loadTransactions();
        } else {
            alert('Error al procesar recarga: ' + result.detail);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión con el servidor');
    }
}

// Process payment
async function processPayment() {
    const amountInput = document.querySelector('.payment-form input[type="number"]');
    const recipientInput = document.querySelector('.payment-form input[type="text"]:first-of-type');
    
    const amount = parseFloat(amountInput?.value) || 0;
    const recipient = recipientInput?.value || '';
    
    if (amount <= 0) {
        alert('Por favor ingrese un monto válido');
        return;
    }
    
    if (!recipient) {
        alert('Por favor ingrese el destinatario');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                qr_data: 'QR' + Math.random().toString(36).substring(7),
                merchant_id: 'MOBILE_APP',
                amount: amount,
                customer_id: recipient,
                reference: 'MOBILE_PAYMENT'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Pago exitoso!\nID: ${result.transaction_id}`);
            closeModal();
            loadTransactions();
        } else {
            alert('Error al procesar pago: ' + result.detail);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión con el servidor');
    }
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch(`${API_URL}/transactions?limit=5`);
        const transactions = await response.json();
        
        const transactionList = document.querySelector('.transaction-list');
        if (transactions.length > 0) {
            transactionList.innerHTML = transactions.map(tx => `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-name">${tx.merchant_id}</div>
                        <div class="transaction-date">${new Date(tx.created_at).toLocaleString()}</div>
                    </div>
                    <div class="transaction-amount">-Bs. ${tx.amount.toFixed(2)}</div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTransactions();
    
    // Update balance periodically
    setInterval(loadTransactions, 10000);
});
