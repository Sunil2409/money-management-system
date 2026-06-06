# 🚀 Deploying Money Manager to Render

Complete step-by-step guide to deploy the Money Manager application to Render.com for production.

---

## Prerequisites

- GitHub account with Money Manager repository pushed
- Render.com account (free tier available)
- Domain name (optional, Render provides subdomain)

---

## Part 1: Create Render Account & Connect GitHub

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Click **Sign up**
3. Choose **Sign up with GitHub** (easiest option)
4. Authorize Render to access your GitHub account
5. Complete the signup process

### Step 2: Create New Web Service

1. Go to Dashboard → **New +**
2. Select **Web Service**
3. Under "GitHub", search for your `money-management-system` repository
4. Click **Connect** next to your repository
5. Click **Create Web Service**

---

## Part 2: Configure Backend Service on Render

### Step 1: Basic Configuration

Fill in the following fields:

| Field | Value |
|-------|-------|
| **Name** | `money-manager-backend` |
| **Environment** | `Docker` |
| **Region** | Choose closest to your users (e.g., Frankfurt, Singapore, US) |
| **Branch** | `main` (or your default branch) |

### Step 2: Build & Start Configuration

**Build Command:**
```bash
# Leave empty - Render will use Dockerfile
```

**Start Command:**
```bash
# Leave empty - Render will use CMD from Dockerfile
```

### Step 3: Environment Variables

Click **Environment** and add the following variables:

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here  # Generate: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Database (Render provides this, we'll set it after creating database)
DATABASE_URL=postgresql://...  # Set after database creation

# Security
SECURE_COOKIE_ENABLED=True
HTTPONLY_COOKIES_ENABLED=True
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Hosts & CORS
ALLOWED_HOSTS=money-manager-backend.render.com,yourdomain.com
CORS_ALLOWED_ORIGINS=https://money-manager-frontend.render.com,https://yourdomain.com

# Redis (set after Redis creation)
REDIS_URL=redis://...  # Set after Redis creation

# Other
DJANGO_ALLOWED_HOSTS=money-manager-backend.render.com
```

**Important**: Generate a strong `SECRET_KEY`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 4: Create Database

1. Go back to Dashboard
2. Click **New +** → **PostgreSQL**
3. Configure:
   - **Name**: `money-manager-db`
   - **Region**: Same as backend service
   - **PostgreSQL Version**: 16
4. Click **Create Database**
5. Wait for database to initialize (2-5 minutes)
6. Go to **Info** tab and copy the **Internal Database URL**
7. Go back to backend service
8. Update `DATABASE_URL` environment variable with the copied URL

### Step 5: Create Redis (Optional but Recommended)

1. Go to Dashboard
2. Click **New +** → **Redis**
3. Configure:
   - **Name**: `money-manager-redis`
   - **Region**: Same as backend service
4. Click **Create Redis**
5. Wait for Redis to initialize
6. Go to **Info** tab and copy the **Internal Redis URL**
7. Go back to backend service
8. Update `REDIS_URL` environment variable with the copied URL

### Step 6: Run Database Migrations

After backend deploys:

1. Go to backend service → **Shell**
2. Run migrations:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

3. Create superuser (optional):
```bash
python manage.py createsuperuser
```

4. Create test user:
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_user('testuser', 'test@example.com', 'test123')
>>> exit()
```

---

## Part 3: Configure Frontend Service on Render

### Step 1: Create Static Site Service

1. Go to Dashboard → **New +**
2. Select **Static Site**
3. Connect your GitHub repository again
4. Configure:
   - **Name**: `money-manager-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `echo 'No build needed'`
   - **Publish Directory**: `frontend`

### Step 2: Add Environment Variables

The frontend doesn't need environment variables for basic setup, but you can add them if using `.env` file in frontend.

### Step 3: Configure Nginx on Render (Optional)

If you want to serve both frontend and backend from Render, create a separate service:

1. Go to Dashboard → **New +** → **Web Service**
2. Use the `nginx/` directory as root
3. Build Command: `echo 'Building'`
4. Start Command: `nginx -g "daemon off;"`

However, **simpler approach**: Serve frontend as Static Site and backend as Web Service separately.

---

## Part 4: Update Frontend API URL

The frontend currently points to `http://localhost`. Update it to use Render backend URL:

### Update `frontend/js/app.js`

```javascript
// Change from:
const API_BASE = '/api';

// To:
const API_BASE = 'https://money-manager-backend.render.com/api';
```

### Update `frontend/js/auth.js`

```javascript
// Change from:
const API_BASE = '/api';

// To:
const API_BASE = 'https://money-manager-backend.render.com/api';
```

### Push changes to GitHub:

```bash
git add frontend/js/app.js frontend/js/auth.js
git commit -m "Update API endpoint for Render production"
git push origin main
```

---

## Part 5: Verify Deployment

### Test Backend

1. Go to backend service URL: `https://money-manager-backend.render.com`
2. You should see the Django welcome page or API docs at `/api/docs/`
3. Test health check: `https://money-manager-backend.render.com/api/health/`

### Test Frontend

1. Go to frontend service URL: `https://money-manager-frontend.render.com`
2. Login page should load
3. Login with `testuser` / `test123`
4. Dashboard should display (may take a moment to load data from backend)

### Test API Endpoints

```bash
# Login
curl -X POST https://money-manager-backend.render.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}' \
  -c cookies.txt

# Get user profile
curl https://money-manager-backend.render.com/api/auth/me/ \
  -b cookies.txt

# Get transactions
curl https://money-manager-backend.render.com/api/transactions/ \
  -b cookies.txt
```

---

## Part 6: Custom Domain (Optional)

### Add Custom Domain to Backend

1. Go to backend service → **Settings** → **Custom Domain**
2. Enter your domain (e.g., `api.yourdomain.com`)
3. Render will provide DNS records to add to your domain registrar
4. Add CNAME record to your domain DNS
5. Wait for DNS propagation (5-10 minutes)

### Add Custom Domain to Frontend

1. Go to frontend service → **Settings** → **Custom Domain**
2. Repeat the same process for frontend domain (e.g., `yourdomain.com`)

### Update CORS in Backend

If using custom domain:

1. Go to backend service → **Environment**
2. Update `ALLOWED_HOSTS`:
```
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com
```

3. Update `CORS_ALLOWED_ORIGINS`:
```
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

---

## Part 7: Monitoring & Troubleshooting

### Check Backend Logs

1. Go to backend service → **Logs**
2. Look for errors like:
   - `ImportError` — missing dependencies
   - `OperationalError` — database connection issue
   - `DisallowedHost` — ALLOWED_HOSTS mismatch

### Check Frontend Logs

1. Go to frontend service → **Logs**
2. Look for 404 errors (missing files) or CORS errors

### Common Issues

#### Issue: `OperationalError: FATAL: terminating connection`
- **Cause**: Database not initialized or connection string wrong
- **Fix**: Go to backend shell and run `python manage.py migrate`

#### Issue: `DisallowedHost` error
- **Cause**: ALLOWED_HOSTS doesn't include Render's domain
- **Fix**: Update `ALLOWED_HOSTS` environment variable

#### Issue: CORS error in browser console
- **Cause**: Frontend and backend domains don't match CORS settings
- **Fix**: Update `CORS_ALLOWED_ORIGINS` environment variable

#### Issue: Static files returning 404
- **Cause**: `collectstatic` not run
- **Fix**: Go to backend shell and run `python manage.py collectstatic --noinput`

#### Issue: 502 Bad Gateway
- **Cause**: Backend service crashed or taking too long
- **Fix**: Check logs, increase timeout, optimize queries

---

## Part 8: Enable Automatic Deployments

### Auto-Deploy on GitHub Push

1. Go to backend service → **Settings**
2. Under **Deploy**, ensure **Auto-Deploy** is **enabled**
3. Every time you push to `main` branch, Render automatically rebuilds and deploys

### Disable Auto-Deploy (if needed)

1. Go to service → **Settings** → **Deploy**
2. Toggle **Auto-Deploy** to OFF
3. Manual deploy via Render Dashboard when ready

---

## Part 9: Production Checklist

Before going live:

- [ ] `DEBUG=False` in environment variables
- [ ] `SECRET_KEY` is a strong random string
- [ ] Database is initialized and migrations run
- [ ] Redis is created and `REDIS_URL` is set
- [ ] `ALLOWED_HOSTS` includes your Render domain and custom domain
- [ ] `CORS_ALLOWED_ORIGINS` matches frontend URL
- [ ] `SECURE_COOKIE_ENABLED=True`
- [ ] `HTTPONLY_COOKIES_ENABLED=True`
- [ ] `SECURE_SSL_REDIRECT=True`
- [ ] Frontend API URL points to backend Render domain
- [ ] Test login/logout functionality
- [ ] Test transaction creation
- [ ] Check logs for errors
- [ ] Set up monitoring alerts (optional)

---

## Part 10: Scaling & Performance

### Increase Backend Capacity

If experiencing slow requests:

1. Go to backend service → **Settings** → **Instance Type**
2. Upgrade from **Free** to **Pro** (if on free tier)
3. Adjust **Number of instances** if needed

### Enable Caching Headers

In `backend/config/settings.py`, add:

```python
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Database Connection Pooling

Render PostgreSQL includes connection pooling. If issues occur:

1. Go to database → **Internal Connection String**
2. Use this URL (includes pooling) instead of regular connection string

---

## Part 11: Backup & Recovery

### Backup Database

Render automatically backs up PostgreSQL. To download backup:

1. Go to database → **Settings** → **Backups**
2. Click download icon next to latest backup
3. Store safely

### Point-in-Time Recovery

If data corruption occurs:

1. Go to database → **Settings** → **Recovery**
2. Choose recovery point (available for 7 days on free tier)
3. Render will restore database to that point

---

## Part 12: Cleanup & Cost Management

### Monitor Usage

1. Go to Account Settings → **Billing**
2. Check current month usage and costs
3. Set spending limit to prevent surprises

### Free Tier Limitations

- Services spin down after 15 minutes of inactivity
- 0.5 GB database storage
- No logs beyond 24 hours

### Upgrade to Pro (Optional)

For production:

```
Pro Tier Benefits:
✅ Always-on (no spin down)
✅ 100 GB+ database storage
✅ 24/7 monitoring
✅ Custom domains included
✅ Priority support
```

---

## Summary

Your Money Manager is now live! 🎉

- **Frontend**: https://money-manager-frontend.render.com
- **Backend**: https://money-manager-backend.render.com
- **Admin**: https://money-manager-backend.render.com/admin/
- **API Docs**: https://money-manager-backend.render.com/api/docs/

### Next Steps

1. Share your app with others
2. Monitor performance in Render Dashboard
3. Collect user feedback
4. Implement new features
5. Scale as traffic grows

---

## Useful Resources

- [Render Documentation](https://render.com/docs)
- [Render Django Guide](https://render.com/docs/deploy-django)
- [Render PostgreSQL Guide](https://render.com/docs/databases)
- [Render Environment Variables](https://render.com/docs/environment-variables)

---

## Support

If you encounter issues:

1. Check Render logs: Service → Logs
2. Check GitHub Actions for build errors
3. Contact Render support: help@render.com
4. Check Money Manager GitHub issues
