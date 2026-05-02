/**
 * Money Manager — Frontend Application (Phase 2: With Auth)
 * Data Flow: User Action → JS Event → fetch() with JWT → Django DRF → Database → JSON → DOM Update
 */
const API_BASE = 'http://127.0.0.1:8000/api';
const CATEGORY_EMOJI = { food:'🍕', transport:'🚗', shopping:'🛍️', bills:'💡', health:'🏥', entertainment:'🎬', salary:'💰', freelance:'💻', investment:'📈', other:'📋' };
const CATEGORY_LABELS = { food:'Food & Dining', transport:'Transport & Fuel', shopping:'Shopping', bills:'Bills & Utilities', health:'Health & Medical', entertainment:'Entertainment', salary:'Salary & Income', freelance:'Freelance Income', investment:'Investments', other:'Miscellaneous' };
const CATEGORY_COLORS = { food:'#f59e0b', transport:'#3b82f6', shopping:'#ec4899', bills:'#8b5cf6', health:'#ef4444', entertainment:'#14b8a6', salary:'#22c55e', freelance:'#0ea5e9', investment:'#10b981', other:'#64748b' };
let deleteTargetId = null;
let currentEditId = null;
let expenseChartInstance = null;

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
  if (res.status === 401 || res.status === 403) {
    // Try refresh
    const refreshed = await refreshToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getToken()}`;
      return fetch(url, { ...options, headers });
    }
    logout();
    return null;
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
  window.location.replace('login.html');
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;
  initTheme(); initNavigation(); initForm(); initFilters(); initModal();
  setDefaultDate(); 
  loadUserProfile();
  loadDashboard(); 
});

// ── User Profile ──
async function loadUserProfile() {
  try {
    const res = await authFetch(`${API_BASE}/auth/me/`);
    if (res && res.ok) {
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
    } else if (!res) {
      // If authFetch returned null/undefined, it means we're logging out
      return;
    } else {
      // If the backend returned a non-200, assume token is completely busted and force logout
      logout();
    }
  } catch (err) { 
    console.error('Profile load error:', err);
    logout(); // Force logout on critical network error for the main profile load
  }
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
    const url = currentEditId ? `${API_BASE}/transactions/${currentEditId}/` : `${API_BASE}/transactions/`;
    const method = currentEditId ? 'PUT' : 'POST';
    const res = await authFetch(url, {
      method: method, body: JSON.stringify(data),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(Object.values(err).flat().join(', ') || 'Failed to save'); }
    showToast(`Transaction ${currentEditId ? 'updated' : 'saved'} successfully!`, 'success');
    resetForm();
    setTimeout(() => {
      // If we were editing, go back to the full list, otherwise dashboard
      if (currentEditId) {
        showSection('transactions');
      } else {
        showSection('dashboard');
      }
    }, 500);
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
  
  currentEditId = null;
  const titleEl = document.getElementById('formTitle');
  const subEl = document.getElementById('formSubtitle');
  const btnEl = document.querySelector('#submitBtn .btn-text');
  if (titleEl) titleEl.textContent = 'Add Transaction';
  if (subEl) subEl.textContent = 'Record a new income or expense';
  if (btnEl) btnEl.textContent = 'Save Transaction';
}

// ── Dashboard ──
async function loadDashboard() {
  try {
    const summaryRes = await authFetch(`${API_BASE}/transactions/summary/`);
    if (summaryRes && summaryRes.ok) {
      const summary = await summaryRes.json();
      animateValue('totalCredited', summary.total_credited);
      animateValue('totalSpent', summary.total_spent);
      animateValue('netBalance', summary.balance);
      document.getElementById('txnCount').textContent = summary.transaction_count;
      
      // Render Chart
      if (summary.category_breakdown) {
        renderChart(summary.category_breakdown);
      }
    }
    const txnRes = await authFetch(`${API_BASE}/transactions/`);
    if (txnRes && txnRes.ok) {
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

// ── Dashboard Chart ──
function renderChart(categoryBreakdown) {
  const canvas = document.getElementById('expenseChart');
  const emptyState = document.getElementById('chartEmpty');
  
  if (!canvas) return;

  const labels = [];
  const data = [];
  const backgroundColors = [];

  // Filter only categories with > 0 spending
  for (const [key, info] of Object.entries(categoryBreakdown)) {
    const amount = parseFloat(info.total);
    if (amount > 0) {
      labels.push(CATEGORY_LABELS[key] || key);
      data.push(amount);
      backgroundColors.push(CATEGORY_COLORS[key] || CATEGORY_COLORS['other']);
    }
  }

  if (data.length === 0) {
    canvas.style.display = 'none';
    emptyState.style.display = 'block';
    return;
  } else {
    canvas.style.display = 'block';
    emptyState.style.display = 'none';
  }

  // Destroy previous instance to avoid hover glitches
  if (expenseChartInstance) {
    expenseChartInstance.destroy();
  }

  // Determine current theme for text color
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#475569';
  const gridColor = isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.08)';

  expenseChartInstance = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: backgroundColors,
        borderWidth: 0,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: textColor,
            padding: 20,
            font: { family: "'Inter', sans-serif", size: 12 }
          }
        },
        tooltip: {
          backgroundColor: isDark ? 'rgba(15, 17, 23, 0.9)' : 'rgba(255, 255, 255, 0.9)',
          titleColor: isDark ? '#f1f5f9' : '#1e293b',
          bodyColor: isDark ? '#94a3b8' : '#475569',
          borderColor: gridColor,
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          usePointStyle: true,
          callbacks: {
            label: function(context) {
              let label = context.label || '';
              if (label) { label += ': '; }
              if (context.parsed !== null) {
                label += '₹' + context.parsed.toLocaleString('en-IN', { minimumFractionDigits: 2 });
              }
              return label;
            }
          }
        }
      }
    }
  });
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
    if (!res) return; // Means it's logging out
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
      <td class="text-center" style="white-space: nowrap;">
        <button class="action-btn" onclick="editTransaction('${txn.id}')" title="Edit">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button class="action-btn" onclick="confirmDelete('${txn.id}')" title="Delete">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </td>
    </tr>`).join('');
}

function formatDate(dateStr) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ── Edit & Delete ──
async function editTransaction(id) {
  try {
    const res = await authFetch(`${API_BASE}/transactions/${id}/`);
    if (!res) return;
    if (!res.ok) throw new Error('Failed to fetch transaction details');
    const txn = await res.json();
    
    currentEditId = id;
    
    // Populate form
    document.getElementById('amount').value = txn.amount;
    document.getElementById('description').value = txn.description || '';
    document.getElementById('date').value = txn.date;
    
    // Status
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    const statusBtn = document.querySelector(`.toggle-btn[data-status="${txn.status}"]`);
    if (statusBtn) statusBtn.classList.add('active');
    document.getElementById('status').value = txn.status;
    
    // Category
    document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
    const catChip = document.querySelector(`.category-chip[data-category="${txn.category}"]`);
    if (catChip) catChip.classList.add('active');
    document.getElementById('category').value = txn.category;
    
    // Update UI headers
    const titleEl = document.getElementById('formTitle');
    const subEl = document.getElementById('formSubtitle');
    const btnEl = document.querySelector('#submitBtn .btn-text');
    if (titleEl) titleEl.textContent = 'Edit Transaction';
    if (subEl) subEl.textContent = 'Update your transaction details';
    if (btnEl) btnEl.textContent = 'Update Transaction';
    
    showSection('add-transaction');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

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
