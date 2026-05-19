# 🔒 Production Hardening Guide for Money Manager

## Overview
This guide covers security hardening required before deploying Money Manager to production. The application includes JWT authentication, multi-user data isolation, and a REST API. Production deployment requires:

1. **Environment-based configuration** (not hardcoded secrets)
2. **Disabled debug mode** (prevents detailed error leakage)
3. **Strict CORS and host whitelisting** (prevents cross-origin attacks)
4. **Secure JWT token management** (prevents token theft)
5. **HTTPS-only communication** (encrypts tokens in transit)
6. **Database hardening** (move from SQLite to PostgreSQL)

---

## 1. Environment Variable Setup

### What was changed
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` now read from environment variables
- The `python-decouple` package handles env var parsing with sensible defaults

### How to use

#### Development (local machine)
```bash
cd backend
pip install -r requirements.txt  # installs python-decouple
# .env file already has defaults, just run:
python manage.py runserver
```

#### Production (deployment environment)
1. Create `.env` file in `backend/` directory with production values:

```bash
# Generate a strong SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Copy output and set in .env:
SECRET_KEY=<your-generated-key>

DEBUG=False  # CRITICAL: Disables detailed error pages
ALLOWED_HOSTS=yourapp.com,www.yourapp.com,api.yourapp.com
CORS_ALLOWED_ORIGINS=https://yourapp.com,https://www.yourapp.com
CORS_ALLOW_ALL_ORIGINS=False  # Always False in production
```

2. Deploy the `.env` file **securely**:
   - Use your hosting platform's secret management (AWS Secrets Manager, Heroku Config Vars, etc.)
   - Never commit `.env` to version control
   - Rotate `SECRET_KEY` periodically

---

## 2. Debug Mode & Error Handling

### Current State
```python
DEBUG=True  # Shows detailed stack traces, static files auto-served
```

### Production State
```python
DEBUG=False  # Hides stack traces, requires static file serving to be configured
```

### Why this matters
- **DEBUG=True** exposes:
  - Full stack traces with local variable values
  - Installed package names and versions
  - File paths on your server
  - Query parameters and POST data (in error messages)
- **Attackers use this information** to craft targeted exploits

### Implementation
Set in `.env`:
```
DEBUG=False
```

---

## 3. ALLOWED_HOSTS Configuration

### Current State (Development)
```python
ALLOWED_HOSTS = []  # Django rejects requests with unrecognized Host header
```

### Production State
```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
# .env:
ALLOWED_HOSTS=yourapp.com,www.yourapp.com,api.yourapp.com
```

### Why this matters
- Prevents **Host Header Injection** attacks
- Ensures DNS rebinding attacks can't reach your app
- Required for Django security middleware to function

### Implementation
```bash
# For example, deploying on yourapp.com:
ALLOWED_HOSTS=yourapp.com,www.yourapp.com,api.yourapp.com
```

---

## 4. CORS Hardening

### Current State (Development)
```python
CORS_ALLOWED_ORIGINS = ['http://localhost:5500', 'http://127.0.0.1:5500']
CORS_ALLOW_ALL_ORIGINS = False  # Now defaults to False (was True, a major security issue)
```

### What Changed
- Removed `CORS_ALLOW_ALL_ORIGINS = True` (was a major security issue)
- All CORS settings now read from environment variables
- Production defaults are secure (only whitelisted origins allowed)

### Production Configuration
```bash
# .env for production:
CORS_ALLOWED_ORIGINS=https://yourapp.com,https://www.yourapp.com
CORS_ALLOW_ALL_ORIGINS=False
```

### Why this matters
- **CORS_ALLOW_ALL_ORIGINS = True** allows **any website** to make requests to your API
- Attackers could steal users' access tokens from localStorage
- This is especially critical since we use `localStorage` for JWT tokens

### Best Practice
```python
# ✅ CORRECT: Explicit whitelist
CORS_ALLOWED_ORIGINS = ['https://yourapp.com', 'https://www.yourapp.com']

# ❌ WRONG: Allows all origins
CORS_ALLOW_ALL_ORIGINS = True

# ❌ WRONG: Allows wildcard (too permissive)
CORS_ALLOWED_ORIGINS = ['*']
```

---

## 5. JWT Token Security & Storage

### Current Architecture
```
User registers → Backend issues access_token (1 day) + refresh_token (7 days)
→ Frontend stores in localStorage
→ Every API call: Authorization: Bearer <access_token>
→ On 401: Frontend auto-refreshes token using refresh_token
```

### Production Concerns

#### Issue 1: localStorage is vulnerable to XSS
**Current implementation:**
```javascript
// frontend/js/auth.js
localStorage.setItem('mm-access-token', tokens.access);
localStorage.setItem('mm-refresh-token', tokens.refresh);
```

**Why it's risky:**
- If attacker injects malicious JS into your page, they can steal tokens
- Stolen tokens can be used to impersonate the user

**Solutions (for future phases):**
1. **httpOnly Cookies** (recommended for production)
   - Browser doesn't expose to JS, only sends with HTTP requests
   - Can't be stolen by XSS (attacker can still perform actions, but can't copy tokens)
   - Requires `CSRF` protection (we'd add it)

2. **Secure Token Endpoint**
   - Issue tokens to backend endpoint, not frontend
   - Frontend never sees tokens, just receives "authenticated" response
   - More complex, but maximum security

**For now (Phase 2):**
- Keep localStorage (acceptable for MVP)
- Add CSRF protection before production
- Use HTTPS (prevents token interception in transit)

#### Issue 2: Refresh Token Rotation
**Current implementation:**
```python
SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,  # ✅ Enabled: each refresh issues a new token
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}
```

**Why it's good:**
- If a refresh token is compromised, it becomes invalid after first use
- Limits window of exposure

---

## 6. HTTPS & Transport Security (CRITICAL)

### Required for Production
```python
# Add to settings.py for HTTPS enforcement:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

### Why this matters
- **Without HTTPS**, tokens can be intercepted during transmission
- Attacker intercepts `Bearer <token>`, then uses it for all requests
- HTTPS encrypts the entire request/response, including tokens

### Implementation
- Use your hosting provider's SSL certificate (AWS ACM, Let's Encrypt, etc.)
- Redirect all HTTP traffic to HTTPS
- Example with Nginx reverse proxy:

```nginx
server {
    listen 80;
    server_name yourapp.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourapp.com;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Authorization $http_authorization;
    }
}
```

---

## 7. Database Hardening

### Current (Development)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### Production Requirements
SQLite is not suitable for production because:
- Not designed for concurrent writes
- No built-in backup/replication
- Limited scalability

**Switch to PostgreSQL:**

1. Install `psycopg2`:
   ```bash
   pip install psycopg2-binary
   ```

2. Update `settings.py` to read from `DATABASE_URL`:
   ```python
   import dj_database_url
   DATABASES = {'default': dj_database_url.config()}
   ```

3. Set `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:password@db.example.com:5432/money_manager
   ```

4. Run migrations on production database:
   ```bash
   python manage.py migrate --noinput
   ```

---

## 8. Security Checklist for Deployment

- [ ] `SECRET_KEY` generated and stored in environment (not in code)
- [ ] `DEBUG = False` in production `.env`
- [ ] `ALLOWED_HOSTS` configured for your domain(s)
- [ ] `CORS_ALLOWED_ORIGINS` restricted to your frontend domain(s)
- [ ] `CORS_ALLOW_ALL_ORIGINS = False`
- [ ] HTTPS enabled (SSL certificate installed)
- [ ] Database migrated to PostgreSQL
- [ ] `.env` file created and deployed to production environment
- [ ] `.env` file NOT committed to version control (in `.gitignore`)
- [ ] `SECURE_SSL_REDIRECT = True` added (redirect HTTP to HTTPS)
- [ ] Refresh token rotation enabled (`ROTATE_REFRESH_TOKENS = True`)
- [ ] Backend running behind a reverse proxy (Nginx, HAProxy)
- [ ] Static files serving configured (S3, CloudFront, or local via Nginx)
- [ ] Regular backups scheduled for PostgreSQL database
- [ ] Logs monitored for suspicious activity
- [ ] Dependencies kept up-to-date (run `pip freeze` and check for security updates)

---

## 9. Example Production Deployment (.env)

```bash
# Generate a strong key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Use the output to create .env:
SECRET_KEY=<your-generated-strong-key>
DEBUG=False
ALLOWED_HOSTS=moneymanager.com,www.moneymanager.com,api.moneymanager.com
CORS_ALLOWED_ORIGINS=https://moneymanager.com,https://www.moneymanager.com
CORS_ALLOW_ALL_ORIGINS=False
DATABASE_URL=postgresql://mm_user:secure_password@db.example.com:5432/money_manager
```

---

## 10. Next Steps

1. **Test locally** with `DEBUG=False`:
   ```bash
   # In .env, set DEBUG=False and run:
   python manage.py collectstatic --noinput
   python manage.py runserver
   ```

2. **Deploy to staging** first to verify all settings work

3. **Enable monitoring** (error tracking, performance, logs)

4. **Plan token rotation** strategy for refresh tokens

5. **Phase 4 roadmap**: Consider httpOnly cookies + CSRF for ultimate security

---

**Note**: This guide covers Django/API security. Frontend security (CSP headers, XSS protection, etc.) will be covered in Phase 5 deployment guide.
