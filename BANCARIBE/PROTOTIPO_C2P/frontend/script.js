const API_URL='http://localhost:8000',WS_URL='ws://localhost:8765';let ws=null,charts={},history=[],alerts=[];

document.addEventListener('DOMContentLoaded',()=>{initCharts();connectWS();fetchMetrics();setInterval(fetchMetrics,5000);});

function connectWS(){try{ws=new WebSocket(WS_URL);ws.onopen=()=>{setConnStatus(true);ws.send(JSON.stringify({type:'subscribe',channel:'all'}));};ws.onmessage=e=>handleWS(JSON.parse(e.data));ws.onclose=()=>{setConnStatus(false);setTimeout(connectWS,3000)};ws.onerror=e=>console.error('WS error:',e);}catch(e){console.error(e);setConnStatus(false);}}

function setConnStatus(c){const el=document.getElementById('connection-status'),ind=document.getElementById('ws-indicator'),st=document.getElementById('ws-status');el.className=c?'badge bg-success':'badge bg-secondary';el.textContent=c?'Conectado':'Desconectado';ind.className=c?'status-indicator bg-success':'status-indicator bg-secondary';st.className=c?'badge bg-success float-end':'badge bg-secondary float-end';st.textContent=c?'Conectado':'Desconectado';}

function handleWS(d){document.getElementById('last-update').textContent='Actualizado: '+new Date().toLocaleTimeString();switch(d.type){case'transaction_update':addTx(d);break;case'metrics_update':updateMetrics(d.metrics);break;case'alert':addAlert(d);break;}}

function initCharts(){charts.tx=new Chart(document.getElementById('transactionsChart'),{type:'line',data:{labels:[],datasets:[{label:'TX/min',data:[],borderColor:'#003B8E',backgroundColor:'rgba(0,59,142,0.1)',tension:0.4,fill:true}]},options:{responsive:true,scales:{y:{beginAtZero:true}}}});charts.st=new Chart(document.getElementById('statusChart'),{type:'doughnut',data:{labels:['OK','Fail','Proc','Init'],datasets:[{data:[0,0,0,0],backgroundColor:['#28a745','#dc3545','#ffc107','#6c757d']}]},options:{responsive:true,plugins:{legend:{position:'bottom'}}}});charts.en=new Chart(document.getElementById('engineChart'),{type:'bar',data:{labels:['Proc','Fail'],datasets:[{data:[0,0],backgroundColor:['#28a745','#dc3545']}]},options:{responsive:true,scales:{y:{beginAtZero:true}}}});}

async function fetchMetrics(){if(ws&&ws.readyState===1)return;try{const r=await fetch(API_URL+'/metrics'),d=await r.json();updateMetrics(d);}catch(e){console.error(e);}}

function updateMetrics(d){document.getElementById('total-transactions').textContent=d.total_transactions||0;document.getElementById('success-rate').textContent=((d.success_rate||0)*100).toFixed(1)+'%';document.getElementById('failed-rate').textContent=((d.failure_rate||0)*100).toFixed(1)+'%';document.getElementById('completed-count').textContent=d.completed||0;document.getElementById('failed-count').textContent=d.failed||0;document.getElementById('pending-count').textContent=d.pending_transactions||0;const rq=d.retry_queue_stats||{};document.getElementById('retry-queue').textContent=rq.pending||0;document.getElementById('retry-success').textContent=rq.retry_success_count||0;updateCharts(d);}

function updateCharts(d){if(charts.st){charts.st.data.datasets[0].data=[d.completed||0,d.failed||0,d.processing||0,d.initiated||0];charts.st.update();}if(charts.en){charts.en.data.datasets[0].data=[d.processed_by_engine||0,d.failed_by_engine||0];charts.en.update();}const now=new Date().toLocaleTimeString();if(!window.txData){window.txData={labels:[],data:[]};}window.txData.labels.push(now);window.txData.data.push(d.total_transactions||0);if(window.txData.labels.length>20){window.txData.labels.shift();window.txData.data.shift();}if(charts.tx){charts.tx.data.labels=window.txData.labels;charts.tx.data.datasets[0].data=window.txData.data;charts.tx.update();}}

function addTx(d){const tx={id:d.transaction_id,state:d.state,time:new Date()};history.unshift(tx);if(history.length>20)history.pop();updateTxList();}

function updateTxList(){const el=document.getElementById('transactions-list');if(!history.length){el.innerHTML='<div class="transaction-item text-muted text-center">Esperando...</div>';return;}el.innerHTML=history.map(t=>`<div class="transaction-item"><div><div class="transaction-id">${t.id.slice(0,12)}...</div><small class="text-muted">${t.time.toLocaleTimeString()}</small></div><span class="transaction-status status-${t.state.toLowerCase()}">${t.state}</span></div>`).join('');}

function addAlert(a){alerts.unshift({msg:a.message,sev:a.severity,time:new Date()});if(alerts.length>10)alerts.pop();document.getElementById('alert-count').textContent=alerts.length;document.getElementById('alerts-container').innerHTML=alerts.map(a=>`<div class="alert-item ${a.sev}"><div>${a.msg}</div><div class="alert-timestamp">${a.time.toLocaleTimeString()}</div></div>`).join('');}

async function simulateBulk(){const c=document.getElementById('sim-count').value,status=document.getElementById('simulation-status');status.className='badge bg-warning';status.textContent='Simulando...';try{const r=await fetch(API_URL+'/simulate/bulk-payments?count='+c,{method:'POST'}),d=await r.json();addAlert({message:`Simulacion: ${d.transaction_count} TX`,severity:'info'});status.className='badge bg-success';status.textContent='Listo';setTimeout(fetchMetrics,2000);}catch(e){console.error(e);status.className='badge bg-danger';status.textContent='Error';}}

function refreshMetrics(){fetchMetrics();}
async function waitForCompletion(){const status=document.getElementById('simulation-status');status.className='badge bg-warning';status.textContent='Esperando...';try{const r=await fetch(API_URL+'/simulate/wait-completion?timeout_seconds=30',{method:'POST'}),d=await r.json();updateMetrics(d.final_metrics);status.className='badge bg-success';status.textContent='Completado';}catch(e){console.error(e);status.className='badge bg-danger';status.textContent='Timeout';}}
function setChartPeriod(p){console.log('Period:',p);}
