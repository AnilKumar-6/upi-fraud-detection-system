const $ = id => document.getElementById(id);

let cachedTransactions = [];

const fmt = n =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(Number(n || 0));

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[char]);
}

function riskClass(value) {
  return value === 'HIGH_RISK'
    ? 'high'
    : value === 'LOW_RISK'
      ? 'low'
      : 'review';
}

function showMessage(message) {
  const element = $('formMessage');
  if (element) element.textContent = message;
}

function renderXai(id, items, valueKey) {
  const element = $(id);
  if (!element) return;

  if (!Array.isArray(items) || items.length === 0) {
    element.innerHTML =
      '<p class="muted">Detailed explanation is not available for this transaction.</p>';
    return;
  }

  const max = Math.max(
    ...items.map(item => Math.abs(Number(item[valueKey] || 0))),
    0.0001
  );

  element.innerHTML = items.slice(0, 6).map(item => {
    const value = Number(item[valueKey] || 0);
    const width = Math.max(2, Math.min(100, Math.abs(value) / max * 100));

    let shown;

    if (valueKey === 'importance' || valueKey === 'relativeImportance') {
      shown = Math.round(value * 100) + '%';
    } else {
      shown = (value > 0 ? '+' : '') + (value * 100).toFixed(1) + ' pts';
    }

    const label = item.label || item.feature || 'Factor';

    return `
      <div class="xai-row">
        <div class="xai-row-top">
          <span>${esc(label)}${
            item.direction ? ' · ' + esc(item.direction) : ''
          }</span>
          <strong>${esc(shown)}</strong>
        </div>
        <div class="xai-track">
          <div class="xai-fill" style="width:${width}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function showTransactionDetails(transaction) {
  $('emptyResult').classList.add('hidden');
  $('result').classList.remove('hidden');

  $('resultBadge').textContent = transaction.prediction || 'REVIEW';
  $('resultBadge').className =
    'risk-badge ' + riskClass(transaction.prediction);

  const riskScore = Number(transaction.riskScore || 0);

  $('score').textContent = Math.round(riskScore * 100) + '%';
  $('meterFill').style.width =
    Math.max(0, Math.min(100, riskScore * 100)) + '%';

  $('source').textContent =
    transaction.predictionSource || 'Not recorded in transaction history';

  $('explanation').textContent =
    transaction.explanation ||
    'The historical record does not contain a saved transaction explanation. Submit a new analysis to view its full explanation, or update the backend to persist explanations for historical transactions.';

  $('mlScore').textContent =
    transaction.mlScore == null
      ? 'Unavailable'
      : Math.round(Number(transaction.mlScore) * 100) + '%';

  $('rulesScore').textContent =
    transaction.rulesScore == null
      ? 'Unavailable'
      : Math.round(Number(transaction.rulesScore) * 100) + '%';

  renderXai(
    'factorList',
    transaction.contributingFactors,
    'contribution'
  );

  renderXai(
    'ruleList',
    transaction.ruleTriggers,
    'contribution'
  );

  renderXai(
    'importanceList',
    transaction.modelFeatureImportance,
    'importance'
  );

  $('xaiMethod').textContent =
    transaction.xaiMethod || 'Transaction-specific explanation method not recorded.';

  $('result').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
}

async function refreshDashboard() {
  try {
    const [summaryRes, txRes] = await Promise.all([
      fetch('/api/dashboard/summary'),
      fetch('/api/transactions')
    ]);

    if (!summaryRes.ok || !txRes.ok) {
      throw new Error('Dashboard API request failed.');
    }

    const summary = await summaryRes.json();
    const transactions = await txRes.json();

    cachedTransactions = Array.isArray(transactions)
      ? transactions
      : [];

    $('total').textContent =
      summary.totalTransactions ?? cachedTransactions.length;

    $('high').textContent = summary.highRisk ?? 0;
    $('review').textContent = summary.needsReview ?? 0;

    const average = cachedTransactions.length
      ? cachedTransactions.reduce(
          (sum, transaction) =>
            sum + Number(transaction.riskScore || 0),
          0
        ) / cachedTransactions.length
      : 0;

    $('averageRisk').textContent =
      Math.round(average * 100) + '%';

    const counts = {
      HIGH_RISK: 0,
      REVIEW: 0,
      LOW_RISK: 0
    };

    cachedTransactions.forEach(transaction => {
      if (Object.hasOwn(counts, transaction.prediction)) {
        counts[transaction.prediction]++;
      }
    });

    const denominator = Math.max(cachedTransactions.length, 1);

    [
      ['HIGH_RISK', 'highCount', 'highBar'],
      ['REVIEW', 'reviewCount', 'reviewBar'],
      ['LOW_RISK', 'lowCount', 'lowBar']
    ].forEach(([risk, countId, barId]) => {
      $(countId).textContent = counts[risk];
      $(barId).style.width =
        (counts[risk] / denominator * 100) + '%';
    });

    renderHistory();
  } catch (error) {
    console.error('Dashboard refresh failed:', error);
    showMessage(
      'Cannot reach the backend. Ensure Spring Boot and MySQL are running.'
    );
  }
}

function renderHistory() {
  const search = ($('historySearch')?.value || '')
    .trim()
    .toLowerCase();

  const filtered = cachedTransactions.filter(transaction =>
    [
      transaction.id,
      transaction.senderUpi,
      transaction.receiverUpi,
      transaction.prediction,
      transaction.transactionType
    ].some(value =>
      String(value ?? '').toLowerCase().includes(search)
    )
  );

  const body = $('historyBody');

  if (!cachedTransactions.length) {
    body.innerHTML =
      '<tr><td colspan="8" class="empty-row">' +
      'No transactions yet. Submit a transaction to build your audit trail.' +
      '</td></tr>';
    return;
  }

  if (!filtered.length) {
    body.innerHTML =
      '<tr><td colspan="8" class="empty-row">' +
      'No transactions match your search.' +
      '</td></tr>';
    return;
  }

  body.innerHTML = filtered.map(transaction => `
    <tr>
      <td>#${esc(transaction.id)}</td>
      <td>${esc(transaction.senderUpi)}</td>
      <td>${esc(transaction.receiverUpi)}</td>
      <td>${fmt(transaction.amount)}</td>
      <td>
        <span class="pill ${riskClass(transaction.prediction)}">
          ${esc(transaction.prediction)}
        </span>
      </td>
      <td>${Math.round(Number(transaction.riskScore || 0) * 100)}%</td>
      <td>${
        transaction.createdAt
          ? esc(new Date(transaction.createdAt).toLocaleString())
          : '—'
      }</td>
      <td>
        <button
          type="button"
          class="view-details-btn"
          data-transaction-id="${esc(transaction.id)}">
          View Details
        </button>
      </td>
    </tr>
  `).join('');
}

async function loadGlobalFeatureImportance() {
  const list = $('importanceList');
  const method = $('xaiMethod');

  try {
    const response = await fetch(
      'http://127.0.0.1:8000/explainability/feature-importance'
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (
      data.modelLoaded === true &&
      Array.isArray(data.features) &&
      data.features.length
    ) {
      renderXai('importanceList', data.features, 'importance');

      method.textContent =
        `Global model importance: ${data.method || 'Feature importance'}. ` +
        (data.note || '');
    } else {
      list.innerHTML =
        '<p class="muted">Model feature importance is unavailable.</p>';
    }
  } catch (error) {
    console.error('Global feature importance failed:', error);
    list.innerHTML =
      '<p class="muted">Could not load global feature importance. Check the Python service and browser console.</p>';
  }
}

$('historyBody').addEventListener('click', event => {
  const button = event.target.closest('[data-transaction-id]');
  if (!button) return;

  const transaction = cachedTransactions.find(
    item => String(item.id) === button.dataset.transactionId
  );

  if (transaction) {
    showTransactionDetails(transaction);
  }
});

$('txForm').addEventListener('submit', async event => {
  event.preventDefault();

  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');

  button.disabled = true;
  showMessage('Analyzing transaction…');

  const formData = new FormData(form);

  const payload = {
    senderUpi: formData.get('senderUpi'),
    receiverUpi: formData.get('receiverUpi'),
    amount: Number(formData.get('amount')),
    transactionType: formData.get('transactionType'),
    hourOfDay: Number(formData.get('hourOfDay')),
    failedAttempts: Number(formData.get('failedAttempts')),
    locationMismatch: form.elements.locationMismatch.checked,
    deviceChanged: form.elements.deviceChanged.checked
  };

  try {
    const response = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.details || data.error || 'Transaction request failed.'
      );
    }

    showTransactionDetails(data);

    showMessage('Transaction saved successfully.');
    await refreshDashboard();

    // Re-display the POST response because it may contain richer
    // explanation fields than the database history response.
    showTransactionDetails(data);
  } catch (error) {
    console.error('Transaction analysis failed:', error);
    showMessage(error.message || 'Transaction analysis failed.');
  } finally {
    button.disabled = false;
  }
});

$('refresh').addEventListener('click', refreshDashboard);
$('historySearch').addEventListener('input', renderHistory);

refreshDashboard();
loadGlobalFeatureImportance();