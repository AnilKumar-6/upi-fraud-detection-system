const $ = id => document.getElementById(id);
let cachedTransactions = [];
const fmt = n => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(n||0));
async function refreshDashboard(){
  try{
    const [summaryRes, txRes] = await Promise.all([fetch('/api/dashboard/summary'),fetch('/api/transactions')]);
    if(!summaryRes.ok||!txRes.ok) throw new Error('API request failed');
    const s=await summaryRes.json(), tx=await txRes.json();
    cachedTransactions=Array.isArray(tx)?tx:[];
    $('total').textContent=s.totalTransactions??0; $('high').textContent=s.highRisk??0; $('review').textContent=s.needsReview??0;
    const average=cachedTransactions.length?cachedTransactions.reduce((sum,t)=>sum+Number(t.riskScore||0),0)/cachedTransactions.length:0;
    $('averageRisk').textContent=Math.round(average*100)+'%';
    const counts={HIGH_RISK:0,REVIEW:0,LOW_RISK:0};
    cachedTransactions.forEach(t=>{if(Object.hasOwn(counts,t.prediction))counts[t.prediction]++;});
    const denominator=Math.max(cachedTransactions.length,1);
    [['HIGH_RISK','highCount','highBar'],['REVIEW','reviewCount','reviewBar'],['LOW_RISK','lowCount','lowBar']].forEach(([risk,countId,barId])=>{
      $(countId).textContent=counts[risk];
      $(barId).style.width=(counts[risk]/denominator*100)+'%';
    });
    renderHistory();
  }catch(e){$('formMessage').textContent='Cannot reach backend. Ensure Spring Boot and MySQL are running.';}
}
function renderHistory(){
 const q=($('historySearch')?.value||'').trim().toLowerCase();
 const filtered=cachedTransactions.filter(t=>[t.id,t.senderUpi,t.receiverUpi,t.prediction,t.transactionType].some(v=>String(v??'').toLowerCase().includes(q)));
 const body=$('historyBody');
 if(!cachedTransactions.length){body.innerHTML='<tr><td colspan="7" class="empty-row">No transactions yet. Submit a transaction to build your audit trail.</td></tr>';return;}
 if(!filtered.length){body.innerHTML='<tr><td colspan="7" class="empty-row">No transactions match your search.</td></tr>';return;}
 body.innerHTML=filtered.map(t=>`<tr><td>#${t.id}</td><td>${esc(t.senderUpi)}</td><td>${esc(t.receiverUpi)}</td><td>${fmt(t.amount)}</td><td><span class="pill ${riskClass(t.prediction)}">${esc(t.prediction)}</span></td><td>${Math.round((t.riskScore||0)*100)}%</td><td>${t.createdAt?new Date(t.createdAt).toLocaleString():'—'}</td></tr>`).join('');
}
function riskClass(v){return v==='HIGH_RISK'?'high':v==='LOW_RISK'?'low':'review'}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('txForm').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget;const btn=f.querySelector('button');btn.disabled=true;$('formMessage').textContent='Analyzing transaction…';
 const d=new FormData(f);const payload={senderUpi:d.get('senderUpi'),receiverUpi:d.get('receiverUpi'),amount:Number(d.get('amount')),transactionType:d.get('transactionType'),hourOfDay:Number(d.get('hourOfDay')),failedAttempts:Number(d.get('failedAttempts')),locationMismatch:f.locationMismatch.checked,deviceChanged:f.deviceChanged.checked};
 try{
  const res=await fetch('/api/transactions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await res.json();if(!res.ok)throw new Error(data.details||data.error||'Request failed');
  $('emptyResult').classList.add('hidden');$('result').classList.remove('hidden');
  $('resultBadge').textContent=data.prediction;$('resultBadge').className='risk-badge '+riskClass(data.prediction);
  $('score').textContent=Math.round((data.riskScore||0)*100)+'%';$('meterFill').style.width=Math.round((data.riskScore||0)*100)+'%';
  $('source').textContent=data.predictionSource;$('explanation').textContent=data.predictionSource==='RULE_BASED_FALLBACK'?'Python service was unavailable; this is a rule-based demo score.':`Prediction returned by the scoring service (${data.predictionSource}).`;
  $('formMessage').textContent='Transaction saved successfully.';await refreshDashboard();
 }catch(err){$('formMessage').textContent=err.message;}finally{btn.disabled=false;}
});
$('refresh').addEventListener('click',refreshDashboard);
$('historySearch').addEventListener('input',renderHistory);
refreshDashboard();
