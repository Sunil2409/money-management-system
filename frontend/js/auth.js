/**
 * Auth Page — Login & Registration Logic
 * Handles JWT token storage and redirects to main app.
 */
const API_BASE = 'http://127.0.0.1:8000/api';

// Apply saved theme
const saved = localStorage.getItem('mm-theme') || 'dark';
document.documentElement.setAttribute('data-theme', saved);

// If already logged in, redirect to app
if (localStorage.getItem('mm-access-token')) {
  window.location.href = 'index.html';
}

// ── Form Toggle ──
document.getElementById('showRegister').addEventListener('click', (e) => {
  e.preventDefault();
  document.getElementById('loginForm').classList.remove('active');
  document.getElementById('registerForm').classList.add('active');
});
document.getElementById('showLogin').addEventListener('click', (e) => {
  e.preventDefault();
  document.getElementById('registerForm').classList.remove('active');
  document.getElementById('loginForm').classList.add('active');
});

// ── Login ──
document.getElementById('loginFormEl').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('loginBtn');
  const errorEl = document.getElementById('loginError');
  errorEl.textContent = '';

  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;

  if (!username || !password) {
    errorEl.textContent = 'Please fill in all fields';
    return;
  }

  btn.classList.add('loading'); btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Invalid credentials');
    }

    const tokens = await res.json();
    localStorage.setItem('mm-access-token', tokens.access);
    localStorage.setItem('mm-refresh-token', tokens.refresh);
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.classList.remove('loading'); btn.disabled = false;
  }
});

// ── Register ──
document.getElementById('registerFormEl').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('registerBtn');
  const errorEl = document.getElementById('registerError');
  errorEl.textContent = '';

  const username = document.getElementById('regUsername').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;

  if (!username || !email || !password) {
    errorEl.textContent = 'Please fill in all fields';
    return;
  }
  if (password.length < 6) {
    errorEl.textContent = 'Password must be at least 6 characters';
    return;
  }

  btn.classList.add('loading'); btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      const msg = Object.values(data).flat().join(', ');
      throw new Error(msg || 'Registration failed');
    }

    const data = await res.json();
    localStorage.setItem('mm-access-token', data.tokens.access);
    localStorage.setItem('mm-refresh-token', data.tokens.refresh);
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.classList.remove('loading'); btn.disabled = false;
  }
});
