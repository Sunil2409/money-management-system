/**
 * Money Manager — Frontend Application (Phase 2: With Auth)
 * Data Flow: User Action → JS Event → fetch() with JWT → Django DRF → Database → JSON → DOM Update
 */
const API_BASE = 'http://127.0.0.1:8000/api';
const CATEGORY_EMOJI = { food:'🍕', transport:'🚗', shopping:'🛍️', bills:'💡', health:'🏥', entertainment:'🎬', salary:'💰', freelance:'💻', investment:'📈', other:'📋' };
const CATEGORY_LABELS = { food:'Food & Dining', transport:'Transport & Fuel', shopping:'Shopping', bills:'Bills & Utilities', health:'Health & Medical', entertainment:'Entertainment', salary:'Salary & Income', freelance:'Freelance Income', investment:'Investments', other:'Miscellaneous' };
let deleteTargetId = null;

// ── Auth Guard ──
function getToken() { return localStorage.getItem('mm-access-token'); }
function requireAuth() {
  if (!getToken()) { window.location.href = 'login.html'; return false; }
  return true;
}

// ── Authenticated Fetch ──
async function authFetch(url, options = {}) {
  const token = getToken();
  if (!token) { window.location.href = 'login.html'; return; }
  const headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
  if (options.body && !options.headers?.['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    // Try refresh
    const refreshed = await refreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getToken()}`;
      return fetch(url, { ...options, headers });
    }
    logout();
    return res;
  }
  return res;
}

async function refreshToken() {
  const refresh = localStorage.getItem('mm-refresh-token');
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem('mm-access-token', data.access);
    if (data.refresh) localStorage.setItem('mm-refresh-token', data.refresh);
    return true;
  } catch { return false; }
}

function logout() {
  localStorage.removeItem('mm-access-token');
  localStorage.removeItem('mm-refresh-token');
  window.location.href = 'login.html';
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;
  initTheme(); initNavigation(); initForm(); initFilters(); initModal();
  setDefaultDate(); loadDashboard(); loadUserProfile();
});

// ── User Profile ──
async function loadUserProfile() {
  try {
    const res = await authFetch(`${API_BASE}/auth/me/`);
    if (res.ok) {
      const user = await res.json();
      const userInfoEl = document.getElementById('userInfo');
      if (userInfoEl) {
        const initial = user.username.charAt(0).toUpperCase();
        userInfoEl.innerHTML = `
          <div class="user-avatar">${initial}</div>
          <div class="user-details">
            <div class="user-name">${user.username}</div>
            <div class="user-email">${user.email}</div>
          </div>`;
      }
    }
  } catch (err) { console.error('Profile load error:', err); }
}

// ── Theme ──
function initTheme() {
  const saved = localStorage.getItem('mm-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  document.getElementById('themeToggle').addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('mm-theme', next);
  });
}

// ── Navigation ──
function initNavigation() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => { e.preventDefault(); showSection(item.dataset.section); });
  });
  const hamburger = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');
  hamburger.addEventListener('click', () => sidebar.classList.toggle('open'));
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => sidebar.classList.remove('open'));
  });
  // Logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) logoutBtn.addEventListener('click', logout);
}

function showSection(sectionId) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const section = document.getElementById(`section-${sectionId}`);
  if (section) section.classList.add('active');
  const navItem = document.querySelector(`.nav-item[data-section="${sectionId}"]`);
  if (navItem) navItem.classList.add('active');
  if (sectionId === 'dashboard') loadDashboard();
  if (sectionId === 'transactions') loadTransactions();
}

// ── Form ──
function initForm() {
  document.querySelectorAll('.toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('status').value = btn.dataset.status;
    });
  });
  document.querySelectorAll('.category-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      document.getElementById('category').value = chip.dataset.category;
    });
  });
  document.getElementById('transactionForm').addEventListener('submit', handleSubmit);
}

function setDefaultDate() {
  document.getElementById('date').value = new Date().toISOString().split('T')[0];
}

async function handleSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  const errorEl = document.getElementById('amountError');
  errorEl.textContent = '';
  const amount = parseFloat(document.getElementById('amount').value);
  if (!amount || amount <= 0) { errorEl.textContent = 'Please enter a valid amount greater than 0'; return; }
  const data = {
    amount: amount.toFixed(2),
    category: document.getElementById('category').value,
    status: document.getElementById('status').value,
    description: document.getElementById('description').value.trim(),
    date: document.getElementById('date').value,
  };
  if (!data.date) { showToast('Please select a date', 'error'); return; }
  btn.classList.add('loading'); btn.disabled = true;
  try {
    const res = await authFetch(`${API_BASE}/transactions/`, {
      method: 'POST', body: JSON.stringify(data),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to save'); }
    showToast('Transaction saved successfully!', 'success');
    resetForm();
    setTimeout(() => showSection('dashboard'), 500);
  } catch (err) { showToast(err.message, 'error'); }
  finally { btn.classList.remove('loading'); btn.disabled = false; }
}

function resetForm() {
  document.getElementById('transactionForm').reset();
  document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.toggle-btn[data-status="spent"]').classList.add('active');
  document.getElementById('status').value = 'spent';
  document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
  document.querySelector('.category-chip[data-category="food"]').classList.add('active');
  document.getElementById('category').value = 'food';
  setDefaultDate();
}

// ── Dashboard ──
async function loadDashboard() {
  try {
    const summaryRes = await authFetch(`${API_BASE}/transactions/summary/`);
    if (summaryRes.ok) {
      const summary = await summaryRes.json();
      animateValue('totalCredited', summary.total_credited);
      animateValue('totalSpent', summary.total_spent);
      animateValue('netBalance', summary.balance);
      document.getElementById('txnCount').textContent = summary.transaction_count;
    }
    const txnRes = await authFetch(`${API_BASE}/transactions/`);
    if (txnRes.ok) {
      const data = await txnRes.json();
      const transactions = Array.isArray(data) ? data : (data.results || []);
      renderRecentTransactions(transactions);
    }
  } catch (err) { console.error('Dashboard load error:', err); }
}

function animateValue(elementId, value) {
  const el = document.getElementById(elementId);
  const num = parseFloat(value) || 0;
  const prefix = elementId === 'txnCount' ? '' : '₹';
  const isNeg = num < 0;
  el.textContent = `${prefix}${isNeg ? '-' : ''}${Math.abs(num).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function renderRecentTransactions(transactions) {
  const container = document.getElementById('recentTransactions');
  const empty = document.getElementById('dashboardEmpty');
  if (!transactions.length) { empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  container.innerHTML = transactions.slice(0, 5).map(txn => `
    <div class="txn-item">
      <div class="txn-emoji">${CATEGORY_EMOJI[txn.category] || '📋'}</div>
      <div class="txn-details">
        <div class="txn-category">${CATEGORY_LABELS[txn.category] || txn.category}</div>
        <div class="txn-desc">${txn.description || txn.date}</div>
      </div>
      <div class="txn-amount ${txn.status}">
        ${txn.status === 'credited' ? '+' : '-'}₹${parseFloat(txn.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </div>
    </div>`).join('');
}

// ── Transactions Table ──
function initFilters() {
  document.getElementById('filterStatus').addEventListener('change', loadTransactions);
  document.getElementById('filterCategory').addEventListener('change', loadTransactions);
}

async function loadTransactions() {
  const status = document.getElementById('filterStatus').value;
  const category = document.getElementById('filterCategory').value;
  let url = `${API_BASE}/transactions/?`;
  const params = [];
  if (status) params.push(`status=${status}`);
  if (category) params.push(`category=${category}`);
  url += params.join('&');
  try {
    const res = await authFetch(url);
    if (!res.ok) throw new Error('Failed to load');
    const data = await res.json();
    const transactions = Array.isArray(data) ? data : (data.results || []);
    renderTable(transactions);
  } catch (err) { showToast('Failed to load transactions', 'error'); }
}

function renderTable(transactions) {
  const tbody = document.getElementById('transactionsBody');
  const empty = document.getElementById('tableEmpty');
  if (!transactions.length) { tbody.innerHTML = ''; empty.style.display = 'block'; return; }
  empty.style.display = 'none';
  tbody.innerHTML = transactions.map(txn => `
    <tr>
      <td>${formatDate(txn.date)}</td>
      <td>${CATEGORY_EMOJI[txn.category] || ''} ${CATEGORY_LABELS[txn.category] || txn.category}</td>
      <td>${txn.description || '—'}</td>
      <td><span class="status-badge ${txn.status}">${txn.status === 'credited' ? 'Income' : 'Expense'}</span></td>
      <td class="text-right" style="font-weight:600;color:${txn.status === 'credited' ? 'var(--green)' : 'var(--red)'}">
        ${txn.status === 'credited' ? '+' : '-'}₹${parseFloat(txn.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
      </td>
      <td class="text-center">
        <button class="action-btn" onclick="confirmDelete('${txn.id}')" title="Delete">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </td>
    </tr>`).join('');
}

function formatDate(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ── Delete ──
function initModal() {
  document.getElementById('cancelDelete').addEventListener('click', closeModal);
  document.getElementById('confirmDelete').addEventListener('click', executeDelete);
  document.getElementById('deleteModal').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeModal(); });
}
function confirmDelete(id) { deleteTargetId = id; document.getElementById('deleteModal').classList.add('active'); }
function closeModal() { document.getElementById('deleteModal').classList.remove('active'); deleteTargetId = null; }
async function executeDelete() {
  if (!deleteTargetId) return;
  try {
    const res = await authFetch(`${API_BASE}/transactions/${deleteTargetId}/`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Delete failed');
    showToast('Transaction deleted', 'info'); closeModal(); loadTransactions(); loadDashboard();
  } catch (err) { showToast(err.message, 'error'); }
}

// ── Toast ──
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
