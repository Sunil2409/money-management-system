# 💰 Money Manager

A modern, full-stack money management application with **secure JWT authentication** to track income and expenses with a clean, responsive UI.

Built with **Django REST Framework** (backend), **httpOnly Cookie-based JWT**, and **Vanilla JavaScript** (frontend).

**🌐 [Live Demo](https://money-manager.onrender.com)** | **📚 [API Documentation (Swagger)](https://money-manager.onrender.com/api/docs/)**

---

![Status](https://img.shields.io/badge/Status-Active-22c55e?style=flat-square)
![CI](https://github.com/Sunil2409/money-management-system/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776ab?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x+-092e20?style=flat-square&logo=django&logoColor=white)
![Security](https://img.shields.io/badge/Auth-httpOnly%20JWT-10b981?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)

---

## ✨ Features

- **🔐 Secure Authentication** — Register & login with httpOnly JWT tokens (XSS-proof)
- **👤 Multi-User Support** — Each user sees only their own transactions
- **💳 Transaction Tracking** — Record income and expenses with amount, category, status, date, and description
- **📊 Dashboard & Analytics** — Summary cards and an interactive Chart.js doughnut chart for visual expense breakdown
- **🏷️ Category System** — 10 built-in categories with emoji icons (Food, Transport, Shopping, Bills, Health, Entertainment, Salary, Freelance, Investment, Other)
- **🔍 Filters & Pagination** — Filter transactions by status/category and paginate results (25 per page)
- **🌙 Dark/Light Mode** — Theme toggle with localStorage persistence
- **📱 Responsive Design** — Works seamlessly on desktop, tablet, and mobile
- **🛡️ Django Admin** — Built-in admin panel for advanced data management
- **🔄 REST API** — Clean RESTful API with full CRUD operations + Swagger/Redoc docs
- **⚡ Rate Limiting** — Brute-force protection on login (5 req/min per IP)
- **📦 Production-Ready** — Multi-stage Docker, PostgreSQL, Redis caching, comprehensive tests

---

## 🔐 Security Features

### httpOnly Cookie-Based Authentication
Unlike traditional localStorage JWT storage (vulnerable to XSS attacks), this application uses:

- **httpOnly Cookies**: JWT tokens stored in browser httpOnly cookies (inaccessible to JavaScript)
- **Secure Flag**: Cookies only sent over HTTPS in production
- **SameSite=Strict/Lax**: CSRF attack prevention (only send on same-domain requests)
- **Automatic Refresh**: Access token auto-refreshes before expiry without user action
- **Environment-Aware**: httpOnly setting is automatically configured based on `DEBUG` mode
  - **Development** (DEBUG=True): httpOnly=False for easier debugging
  - **Production** (DEBUG=False): httpOnly=True for maximum security
  - Override via `HTTPONLY_COOKIES_ENABLED` environment variable

This eliminates the risk of XSS attacks stealing authentication tokens in production environments.

### Rate Limiting
- Login/Register endpoints: **5 requests per minute per IP** (brute-force protection)
- General API: **20 requests per minute** (anonymous), **60 requests per minute** (authenticated)

### Additional Security
- CSRF protection via Django middleware
- CORS restricted to configured origins only
- SQL injection prevention (Django ORM)
- Password validation (minimum length + complexity)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x + Django REST Framework |
| **Authentication** | SimpleJWT + httpOnly Cookies |
| **Frontend** | HTML5 + Vanilla CSS + JavaScript |
| **Database** | PostgreSQL (production), SQLite (dev) |
| **Caching** | Redis (session & query caching) |
| **API Docs** | drf-spectacular (OpenAPI 3.0, Swagger UI, Redoc) |
| **Containerization** | Docker + Docker Compose (multi-stage builds, non-root user) |
| **CI/CD** | GitHub Actions (lint, test with 80%+ coverage, Docker build) |
| **Design** | Dark-mode-first, Glassmorphism, Inter font |

---

## 📁 Project Structure

```
MoneyManager/
├── backend/                      # Django project
│   ├── manage.py
│   ├── pytest.ini                # Test configuration
│   ├── config/                   # Project settings
│   │   ├── settings.py           # DRF, JWT, CORS, drf-spectacular config
│   │   ├── urls.py               # Root URL routing + API docs
│   │   ├── authentication.py     # CookieJWTAuthentication
│   │   ├── exceptions.py         # Custom exception handler
│   │   └── wsgi.py
│   ├── accounts/                 # Auth app
│   │   ├── views.py              # Register, login, logout, /me
│   │   ├── serializers.py        # User & registration serializers
│   │   ├── urls.py               # Auth routes
│   │   ├── tests.py              # Auth endpoint tests
│   │   └── models.py
│   ├── transactions/             # Core app
│   │   ├── views.py              # CRUD + summary (paginated, cached)
│   │   ├── models.py             # Transaction model (UUID, user-scoped)
│   │   ├── serializers.py        # Transaction serializers + validation
│   │   ├── urls.py               # DRF router
│   │   ├── tests.py              # Comprehensive CRUD & filtering tests
│   │   └── admin.py
│   ├── Dockerfile                # Multi-stage production build
│   ├── entrypoint.sh             # Wait for DB, run migrations
│   ├── requirements.txt          # Production dependencies
│   └── requirements-dev.txt      # Dev dependencies (pytest, flake8)
├── frontend/                     # Static frontend
│   ├── index.html                # Main app (requires auth)
│   ├── login.html                # Login/Register page
│   ├── css/
│   │   ├── styles.css            # Design system
│   │   └── auth.css              # Auth page styles
│   └── js/
│       ├── app.js                # Main app logic (cookie auth)
│       └── auth.js               # Login/register (cookie handling)
├── nginx/                        # Reverse proxy config
│   └── nginx.conf
├── docker-compose.yml            # Full stack orchestration
├── .env.example                  # Environment template
├── .github/workflows/ci.yml      # GitHub Actions CI pipeline
├── README.md                     # This file
└── money_manager_deep_dive.md    # Architecture & design decisions
```

---

## 🚀 Quick Start

### Development (Local)

#### Prerequisites
- Python 3.12+, pip
- PostgreSQL 16+ (optional, uses SQLite by default)

#### Setup

```bash
# Clone repository
git clone https://github.com/Sunil2409/money-management-system.git
cd money-management-system

# Backend setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
cd backend
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver 8000

# Frontend setup (new terminal)
cd frontend
python3 -m http.server 5500

# Open http://127.0.0.1:5500 in browser
```

---

### Production (Docker)

```bash
# Build and run all services
docker compose up -d --build

# Check logs
docker compose logs -f backend

# Stop all services
docker compose down
```

The app will be available at **http://localhost** (port 80).

**Important**: Before deploying to production, update `.env`:
```bash
cp .env.example .env
# Edit .env with production values:
# - SECRET_KEY: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
# - DEBUG=False (CRITICAL: Disables debug mode)
# - HTTPONLY_COOKIES_ENABLED=True (for XSS protection)
# - SECURE_COOKIE_ENABLED=True (requires HTTPS)
# - SECURE_SSL_REDIRECT=True
# - SESSION_COOKIE_SECURE=True
# - CSRF_COOKIE_SECURE=True
# - Database credentials
# - ALLOWED_HOSTS (add your domain)
# - CORS_ALLOWED_ORIGINS (add your frontend URL)
```

---

## 🔐 Authentication Flow

```
┌─ REGISTER ───────────────────────┐
│                                   │
│ 1. POST /api/auth/register/       │
│    { username, email, password }  │
│                                   │
│ 2. Backend validates & creates    │
│    user, generates JWT tokens     │
│                                   │
│ 3. Sets httpOnly cookies:         │
│    - access_token (1 day)         │
│    - refresh_token (7 days)       │
│                                   │
│ 4. Frontend redirects to app      │
└───────────────────────────────────┘

┌─ LOGIN ───────────────────────────┐
│                                    │
│ 1. POST /api/auth/login/           │
│    { username, password }          │
│                                    │
│ 2. Backend validates credentials   │
│    generates JWT tokens            │
│                                    │
│ 3. Sets httpOnly cookies           │
│    (automatic browser handling)    │
│                                    │
│ 4. Frontend redirects to app       │
└────────────────────────────────────┘

┌─ API REQUESTS ────────────────────┐
│                                    │
│ 1. fetch(url, {                   │
│    credentials: 'include'         │ ← Include cookies
│  })                               │
│                                    │
│ 2. Browser automatically sends    │
│    access_token cookie             │
│                                    │
│ 3. Backend validates token via    │
│    CookieJWTAuthentication        │
│                                    │
│ 4. On 401 (expired):              │
│    Auto-refresh from refresh_token│
│    Set new access_token cookie    │
│    Retry original request          │
└────────────────────────────────────┘

┌─ LOGOUT ──────────────────────────┐
│                                    │
│ 1. POST /api/auth/logout/         │
│                                    │
│ 2. Backend clears cookies         │
│    (max_age=0)                    │
│                                    │
│ 3. Frontend redirects to login    │
└────────────────────────────────────┘
```

---

## 📡 API Endpoints

### Interactive Documentation

- **Swagger UI**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) (interactive, test endpoints)
- **ReDoc**: [http://localhost:8000/api/docs/redoc/](http://localhost:8000/api/docs/redoc/) (read-only, prettier)
- **OpenAPI Schema**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/) (JSON)

### Authentication Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|-----------|
| `POST` | `/api/auth/register/` | Create account (sets httpOnly cookies) | 5/min |
| `POST` | `/api/auth/login/` | Login (sets httpOnly cookies) | 5/min |
| `POST` | `/api/auth/token/refresh/` | Refresh access token (uses refresh cookie) | 60/min |
| `GET` | `/api/auth/me/` | Get current user profile | 60/min |
| `POST` | `/api/auth/logout/` | Logout (clears cookies) | 60/min |

### Transaction Endpoints (requires auth)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/transactions/?page=1` | List user's transactions (paginated, 25/page) | ✅ |
| `POST` | `/api/transactions/` | Create a new transaction | ✅ |
| `GET` | `/api/transactions/{id}/` | Retrieve a transaction | ✅ |
| `PUT` | `/api/transactions/{id}/` | Update a transaction | ✅ |
| `DELETE` | `/api/transactions/{id}/` | Delete a transaction | ✅ |
| `GET` | `/api/transactions/summary/` | Get spending summary & stats (cached) | ✅ |

### Query Parameters

```bash
# Filter by status
GET /api/transactions/?status=spent

# Filter by category
GET /api/transactions/?category=food

# Pagination
GET /api/transactions/?page=2

# Combine filters & pagination
GET /api/transactions/?status=spent&category=food&page=1
```

---

## 🧪 Testing

```bash
cd backend

# Run all tests with coverage
pytest -v --cov --cov-report=term-missing --cov-fail-under=80

# Run specific test file
pytest accounts/tests.py -v

# Run with verbose output
pytest -v --tb=short
```

**Current Coverage**: 80%+ (accounts auth + transactions CRUD)

---

## 🗂️ Roadmap

- [x] Phase 1 — Core CRUD + Responsive UI
- [x] Phase 2 — User Authentication (JWT)
- [x] Phase 3 — Dashboard Charts (Chart.js)
- [x] Phase 3.5 — Security Audit (httpOnly cookies, rate limiting, tests)
- [x] Phase 3.6 — API Documentation (Swagger/Redoc)
- [ ] Phase 4 — Budget Alerts & Notifications
- [ ] Phase 5 — Recurring Transactions & Templates
- [ ] Phase 6 — AWS Deployment (ECS + RDS + S3 + CloudFront)
- [ ] Phase 7 — Mobile App (React Native)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests & ensure 80%+ coverage (`pytest --cov --cov-fail-under=80`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Sunil Kumar E**

---

## 🔗 Resources

- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [JWT Security Best Practices](https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/)
- [OWASP Cheat Sheet: Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

<p align="center">
  <img src="https://img.shields.io/badge/Made%20with-Django%20%2B%20JavaScript-blue?style=for-the-badge" alt="Made with Django + JavaScript">
  <br/>
  Built with ❤️ by Sunil Kumar E
</p>

