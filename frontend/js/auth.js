/**
 * Auth Page — Login & Registration Logic (httpOnly Cookie-based)
 * 
 * Security: Tokens are stored in httpOnly cookies by the server.
 * Frontend no longer handles token storage/retrieval.
 * All API requests automatically include cookies (credentials: 'include').
 */

// Detect API base URL (supports both dev and prod environments)
const API_BASE = window.location.origin.includes('localhost') 
  ? 'http://127.0.0.1:8000/api'
  : `${window.location.origin}/api`;

// Apply saved theme
const saved = localStorage.getItem('mm-theme') || 'dark';
document.documentElement.setAttribute('data-theme', saved);

/**
 * Check if user is already authenticated by attempting to fetch /me
 * If authenticated (has valid access_token cookie), redirect to app
 */
async function checkAuthentication() {
  try {
    const res = await fetch(`${API_BASE}/auth/me/`, {
      method: 'GET',
      credentials: 'include', // Include cookies in request
    });
    
    if (res.ok) {
      // User is authenticated, redirect to main app
      window.location.href = 'index.html';
    }
  } catch (err) {
    // Not authenticated, stay on login page
    console.debug('Not authenticated:', err.message);
  }
}

// Check authentication on page load
checkAuthentication();

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

  btn.classList.add('loading');
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Include cookies in request (receives Set-Cookie response)
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || data.error?.message || 'Invalid credentials');
    }

    // Success! Tokens are now in httpOnly cookies (set by server via Set-Cookie header)
    // Redirect to app
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
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

  btn.classList.add('loading');
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Include cookies in request (receives Set-Cookie response)
      body: JSON.stringify({ username, email, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      const msg = data.detail || Object.values(data).flat().join(', ');
      throw new Error(msg || 'Registration failed');
    }

    // Success! Tokens are now in httpOnly cookies
    // Redirect to app
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
});
