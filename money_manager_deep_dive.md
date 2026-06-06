# 💰 Money Manager — Complete Architectural Deep Dive

> **Audience**: Mid-level engineers preparing for a senior/staff-level technical interview.  
> **Goal**: Understand every architectural decision well enough to defend it under scrutiny.

---

## Table of Contents

1. [The Tech Stack Matrix](#1-the-tech-stack-matrix) — Role and synergy of every technology
2. [The Request Lifecycle](#2-the-request-lifecycle) — Trace a request end-to-end
3. [The 'Why': Design Patterns & Code Organization](#3-the-why-design-patterns--code-organization) — Architectural rationale
4. [Translation for Operations](#4-translation-for-operations) — Bridging code to cloud infrastructure
5. [Security Architecture](#5-security-architecture)
6. [Testing Strategy](#6-testing-strategy)
7. [Interview Talking Points](#7-interview-talking-points)

---

## 1. The Tech Stack Matrix

### 1.1 Technology Inventory — What Each Piece Does

| Layer | Technology | Version | Concrete Role in This System |
|-------|-----------|---------|------------------------------|
| **Backend Framework** | Django 5.x+ | `>=5.0,<7.0` | Request/response cycle, ORM, admin panel, URL routing, middleware pipeline, settings management |
| **API Layer** | Django REST Framework | `>=3.15` | Serialization/deserialization, ViewSets for CRUD, pagination, throttling, browsable API, router-based URL generation |
| **Authentication** | SimpleJWT | `>=5.3` | JWT issuance, validation, refresh token rotation. Extended with custom `CookieJWTAuthentication` for httpOnly cookie extraction |
| **Database (Dev)** | SQLite | Bundled | Zero-config local development. File-based, no daemon needed |
| **Database (Prod)** | PostgreSQL 16 | Via `psycopg2-binary` | Concurrent writes, ACID transactions, connection pooling (via Gunicorn workers), proper backup/replication support |
| **Caching** | Redis 7 | Via `django-redis` | Per-user summary query cache (5-min TTL), cache-aside pattern. Fallback to `LocMemCache` in dev without Redis |
| **WSGI Server** | Gunicorn | `>=22.0` | Pre-fork worker model. 3 workers configured. Handles concurrent HTTP connections. Entrypoint for the Docker container |
| **Reverse Proxy** | Nginx (Alpine) | Latest | Static file serving (frontend HTML/CSS/JS + Django admin static files), gzip compression, request proxying to Gunicorn with proper headers (`X-Forwarded-For`, `X-Forwarded-Proto`) |
| **API Documentation** | drf-spectacular | `>=0.26` | Auto-generated OpenAPI 3.0 schema from DRF serializers/views. Swagger UI for interactive testing, ReDoc for readable docs |
| **CORS** | django-cors-headers | `>=4.0` | Adds `Access-Control-Allow-Origin` headers. Configured per-environment via env vars. `CORS_ALLOW_CREDENTIALS = True` for cookie-based auth |
| **Filtering** | django-filter | `>=24.0` | Declarative query parameter filtering on ViewSets (`filterset_fields = ['status', 'category', 'date']`) |
| **Config Management** | python-decouple | `>=3.8` | Reads from `.env` file and OS environment variables. Provides type casting (`cast=bool`, `cast=Csv()`). Sensible defaults for dev |
| **Containerization** | Docker + Compose | Multi-stage | Builder stage installs deps, production stage copies only what's needed. Non-root user (`appuser`). Health checks on all services |
| **CI/CD** | GitHub Actions | (`.github/workflows/ci.yml`) | Lint (flake8), test (pytest with 80% coverage gate), Docker build verification |
| **Frontend** | Vanilla HTML/CSS/JS | No framework | SPA-like behavior via section toggling. Chart.js for doughnut chart. `fetch()` with `credentials: 'include'` for cookie auth |

### 1.2 Why These Tools Work Well Together

**Django + DRF + SimpleJWT** form a vertically integrated auth-to-API pipeline. DRF's `DEFAULT_AUTHENTICATION_CLASSES` slot naturally accepts our custom `CookieJWTAuthentication`, and DRF's permission system (`IsAuthenticated`) plugs directly into it. No middleware gymnastics — it's all first-class.

**Redis + django-redis + DRF ViewSets** create a clean cache-aside pattern. The `summary` action checks Redis → computes on miss → writes back with TTL. Cache invalidation is explicit: every `perform_create/update/destroy` calls `cache.delete(f'summary_{user.id}')`. This is the textbook cache-aside strategy, and it works because the cache key namespace is small and predictable.

**Nginx → Gunicorn → Django** follows the standard Python web serving pyramid. Nginx handles slow clients, buffers requests, serves static assets, and terminates SSL — all things Gunicorn is bad at. Gunicorn's pre-fork model maps well to Django's synchronous request handling. 3 workers × 1 thread each = 3 concurrent requests, which is appropriate for an I/O-bound CRUD API.

**PostgreSQL + Redis** is the classic OLTP caching pair. PostgreSQL handles relational integrity (user FK, indexed queries), Redis absorbs repeated read traffic (summary aggregation queries are expensive — multiple `SUM` + `GROUP BY` queries).

**Docker Multi-Stage Build** keeps the production image small. The builder stage installs `gcc` and `libpq-dev` to compile `psycopg2`, then the final stage only copies the compiled artifacts. Final image has no compiler, no dev headers — reduced attack surface.

---

## 2. The Request Lifecycle

### 2.1 Full Trace: `POST /api/transactions/` (Create Transaction)

This traces a single authenticated write — the most complex path through the system because it touches auth, validation, ORM, cache invalidation, and logging.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Browser → Nginx (Port 80)                                       │
│                                                                         │
│   The browser sends:                                                     │
│   POST /api/transactions/ HTTP/1.1                                      │
│   Host: localhost                                                       │
│   Cookie: access_token=eyJhbGciOi...                                    │
│   Content-Type: application/json                                        │
│   Body: {"amount":"250.00","category":"food","status":"spent",          │
│          "description":"Lunch","date":"2026-05-01"}                     │
│                                                                         │
│   The Cookie header is automatically attached by the browser            │
│   because the cookie was set with path="/" and the fetch() call         │
│   used credentials: 'include'.                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: Nginx Reverse Proxy                                             │
│                                                                         │
│   nginx.conf matches location /api/ → proxy_pass http://django;        │
│                                                                         │
│   Nginx adds headers:                                                    │
│     X-Real-IP: <client IP>                                             │
│     X-Forwarded-For: <client IP>                                       │
│     X-Forwarded-Proto: http                                            │
│     Host: localhost                                                     │
│                                                                         │
│   Gzip is configured but not applied here (request, not response).      │
│   proxy_read_timeout is 300s — prevents hanging connections.            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Gunicorn → Django WSGI                                          │
│                                                                         │
│   Gunicorn (3 workers, pre-fork) accepts the connection.                 │
│   One worker picks up the request.                                       │
│   Calls config/wsgi.py → Django's WSGI handler.                         │
│                                                                         │
│   config/wsgi.py:                                                        │
│     application = get_wsgi_application()                                 │
│                                                                         │
│   This is a thin wrapper — Django's WSGI handler initializes the        │
│   middleware stack and dispatches the request.                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Django Middleware Pipeline (Bottom → Top Order)                  │
│                                                                         │
│   MIDDLEWARE order as defined in settings.py:                           │
│                                                                         │
│   ┌─────────────────────────────────────────┐                           │
│   │ 1. SecurityMiddleware                   │                           │
│   │    - Checks SECURE_SSL_REDIRECT         │                           │
│   │    - Sets X-Content-Type-Options        │                           │
│   │    - Sets X-Frame-Options (clickjack)   │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 2. SessionMiddleware                    │                           │
│   │    - Reads session cookie (not used     │                           │
│   │      for JWT auth, but present for      │                           │
│   │      Django admin/sessions)             │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 3. CorsMiddleware                       │                           │
│   │    - Checks Origin header               │                           │
│   │    - Adds Access-Control-Allow-Origin   │                           │
│   │      if origin is in CORS_ALLOWED_ORIGINS│                          │
│   │    - Adds Access-Control-Allow-Credentials│                         │
│   │    - Handles preflight OPTIONS requests  │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 4. CommonMiddleware                     │                           │
│   │    - URL normalization (trailing slash)  │                           │
│   │    - Appends slash if needed            │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 5. CsrfViewMiddleware                   │                           │
│   │    - CSRF token check (skipped for      │                           │
│   │      JWT-authenticated API calls        │                           │
│   │      because they use Bearer/cookie,    │                           │
│   │      not session-based forms)           │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 6. AuthenticationMiddleware             │                           │
│   │    - Sets request.user (from session)   │                           │
│   │    - DRF will override this later via   │                           │
│   │      CookieJWTAuthentication            │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 7. MessageMiddleware                    │                           │
│   │    - Flash messages (admin panel only)  │                           │
│   ├─────────────────────────────────────────┤                           │
│   │ 8. XFrameOptionsMiddleware              │                           │
│   │    - Anti-clickjacking header           │                           │
│   └─────────────────────────────────────────┘                           │
│                                                                         │
│   All middleware pass — request continues to URL routing.                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: URL Resolution                                                   │
│                                                                         │
│   config/urls.py matches:                                                │
│     path("api/", include("transactions.urls"))                          │
│                                                                         │
│   transactions/urls.py:                                                  │
│     router = DefaultRouter()                                             │
│     router.register(r'transactions', TransactionViewSet)                 │
│                                                                         │
│   DRF DefaultRouter generates:                                           │
│     POST /api/transactions/ → TransactionViewSet.create()               │
│                                                                         │
│   The router auto-generates URL patterns from the ViewSet's actions.     │
│   POST maps to the `create` method inherited from CreateModelMixin.     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 6: DRF Authentication (CookieJWTAuthentication)                     │
│                                                                         │
│   Before the view executes, DRF runs its authentication classes:         │
│                                                                         │
│   CookieJWTAuthentication.authenticate(request):                         │
│     1. Tries request.COOKIES.get('access_token')                        │
│        → Finds the httpOnly cookie (browser sent it automatically)      │
│     2. If no cookie, falls back to Authorization: Bearer header         │
│        (for API testing tools like curl/httpie)                         │
│     3. Calls self.get_validated_token(access_token)                     │
│        → SimpleJWT validates:                                            │
│          - Token signature (HMAC with SECRET_KEY)                        │
│          - Token expiry (exp claim)                                      │
│          - Token type (access vs refresh)                                │
│     4. Calls self.get_user(validated_token)                             │
│        → Extracts user_id from token payload                            │
│        → Looks up User in database                                       │
│        → Returns (user, validated_token) tuple                           │
│                                                                         │
│   request.user = <User: sunil>                                           │
│   request.auth = <ValidatedToken>                                        │
│                                                                         │
│   Then DRF checks permissions: IsAuthenticated → passes.                 │
│                                                                         │
│   Then DRF checks throttling: UserRateThrottle →                         │
│     Key: user_<user_id> → 60/min limit → passes.                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 7: View Execution — TransactionViewSet.create()                     │
│                                                                         │
│   Inherited from DRF's CreateModelMixin:                                 │
│                                                                         │
│   1. request.data is parsed (JSON → Python dict)                         │
│   2. TransactionSerializer(data=request.data) is instantiated            │
│   3. serializer.is_valid() is called:                                    │
│                                                                         │
│      a. Field-level validation:                                          │
│         - amount: must be Decimal, validate_amount() checks > 0         │
│         - category: must be one of CATEGORY_CHOICES                     │
│         - status: must be one of STATUS_CHOICES                         │
│         - date: must be valid ISO date                                  │
│                                                                         │
│      b. Object-level validation (validate() method):                    │
│         - None defined in this serializer                               │
│                                                                         │
│   4. If invalid → 400 response with error details:                      │
│      {                                                                   │
│        "error": {                                                        │
│          "code": "validation_error",                                     │
│          "message": "Validation failed.",                                │
│          "details": {"amount": ["Amount must be greater than zero."]}   │
│        }                                                                 │
│      }                                                                   │
│      (Formatted by custom_exception_handler)                             │
│                                                                         │
│   5. If valid → serializer.save() is called                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 8: ORM → Database                                                    │
│                                                                         │
│   serializer.save() calls perform_create(serializer):                   │
│                                                                         │
│     def perform_create(self, serializer):                                │
│         instance = serializer.save(user=self.request.user)               │
│                                                                         │
│   This sets the user FK before saving. Django ORM generates:             │
│                                                                         │
│     INSERT INTO transactions_transaction (                               │
│       id, user_id, amount, category, status, description,               │
│       date, created_at, updated_at                                       │
│     ) VALUES (                                                           │
│       'a1b2c3d4-...',  -- UUID generated by Python uuid.uuid4()         │
│       <user_id>,       -- FK from request.user                           │
│       '250.00',        -- Decimal field                                  │
│       'food',           -- CharField with choices                        │
│       'spent',          -- CharField with choices                        │
│       'Lunch',          -- TextField (optional)                          │
│       '2026-05-01',     -- DateField                                     │
│       NOW(),            -- auto_now_add                                  │
│       NOW()             -- auto_now                                      │
│     )                                                                    │
│                                                                         │
│   PostgreSQL: The query is parameterized (no SQL injection possible).   │
│   The UUID PK is generated in Python, not by the DB.                    │
│                                                                         │
│   ORM returns the Transaction instance with all fields populated.       │
│                                                                         │
│   BACK IN perform_create():                                              │
│     cache.delete(f'summary_{self.request.user.id}')                     │
│     → Invalidates the Redis cache key for this user's summary            │
│     → Next GET /api/transactions/summary/ will recompute                 │
│                                                                         │
│     logger.info("Transaction created: id=%s user=%s amount=%s...")      │
│     → Structured log entry for audit trail                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 9: Response Serialization & Return                                   │
│                                                                         │
│   DRF serializes the Transaction instance back to JSON:                  │
│                                                                         │
│   {                                                                      │
│     "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",                      │
│     "amount": "250.00",                                                 │
│     "category": "food",                                                  │
│     "category_display": "Food & Dining",  ← Computed by serializer      │
│     "status": "spent",                                                   │
│     "status_display": "Spent",            ← Computed by serializer      │
│     "description": "Lunch",                                              │
│     "date": "2026-05-01",                                               │
│     "created_at": "2026-05-01T11:30:00.000000+05:30",                  │
│     "updated_at": "2026-05-01T11:30:00.000000+05:30"                   │
│   }                                                                      │
│                                                                         │
│   Status code: 201 Created                                               │
│                                                                         │
│   Middleware processes response in reverse (top → bottom):               │
│     - CorsMiddleware adds CORS headers                                   │
│     - SecurityMiddleware adds security headers                           │
│     - Gzip (via Nginx, not Django) compresses the response body         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 10: Gunicorn → Nginx → Browser Response                              │
│                                                                         │
│   Gunicorn worker sends the HTTP response back to Nginx.                 │
│   Nginx:                                                                 │
│     - Applies gzip compression (Content-Encoding: gzip)                  │
│     - Sets connection: keep-alive or close                               │
│     - Returns response to client                                         │
│                                                                         │
│   Browser receives 201 Created.                                          │
│   Frontend (app.js):                                                     │
│     1. Parses JSON response                                              │
│     2. showToast("Transaction saved successfully!")                     │
│     3. resetForm() → clears the form                                     │
│     4. Navigates to Dashboard                                            │
│     5. loadDashboard() → fetches summary + recent transactions          │
│        (summary now computed fresh because cache was invalidated)        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Read Path: `GET /api/transactions/summary/` (Cached)

The summary endpoint demonstrates the **cache-aside** pattern:

```
                     ┌──────────┐
    Request ────────▶│ ViewSet  │
                     │ summary()│
                     └────┬─────┘
                          │
                    cache.get(f'summary_{user.id}')
                          │
              ┌───────────┴───────────┐
              │                       │
           HIT │                   MISS│
              ▼                       ▼
     ┌──────────────┐    ┌─────────────────────────┐
     │ Return cached │    │ Run 3 aggregation queries│
     │ JSON directly │    │ against PostgreSQL:       │
     └──────────────┘    │                            │
                         │ 1. Sum spent amounts       │
                         │ 2. Sum credited amounts    │
                         │ 3. GROUP BY category        │
                         │                            │
                         │ cache.set(key, result, 300)│
                         │ → Write to Redis           │
                         │ → 5-minute TTL              │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │ Return result │
                              │ as JSON       │
                              └──────────────┘
```

**Cache invalidation**: Every `perform_create`, `perform_update`, and `perform_destroy` calls `cache.delete(f'summary_{user.id}')`. This is an **explicit invalidation** strategy — the write side knows exactly which cache key to purge. No TTL guessing, no stale reads.

**Why per-user keys?** Multi-user system. User A adding a transaction should not invalidate User B's cache. The key namespace `summary_{user_id}` guarantees isolation.

### 2.3 Token Refresh Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ Token expired scenario:                                           │
│                                                                   │
│ 1. Browser sends GET /api/transactions/ with expired access_token │
│ 2. CookieJWTAuthentication detects expired token → 401            │
│ 3. Frontend authFetch() catches 401:                              │
│    a. Calls POST /api/auth/token/refresh/                         │
│       → CustomTokenRefreshView reads refresh_token from cookie    │
│       → SimpleJWT validates refresh token                         │
│       → SimpleJWT issues NEW access token (ROTATE_REFRESH_TOKENS) │
│       → Sets new access_token cookie in response                  │
│    b. Retries the original GET /api/transactions/                 │
│       → Browser automatically sends the new access_token cookie   │
│ 4. User never sees a login screen — the refresh is transparent     │
└──────────────────────────────────────────────────────────────────┘
```

This is **silent token refresh** — a better UX than forcing re-login every time the access token expires. The rotation of refresh tokens (`ROTATE_REFRESH_TOKENS = True`) means stolen refresh tokens become useless after the legitimate user uses theirs once (replay detection by invalidation).

---

## 3. The 'Why': Design Patterns & Code Organization

### 3.1 Project Structure: Django's App Pattern

```
backend/
├── config/          # Project-level configuration (Django's "project")
│   ├── settings.py         # All Django/DRF/third-party settings
│   ├── urls.py             # Root URL router
│   ├── authentication.py   # Custom auth class (CookieJWTAuthentication)
│   ├── exceptions.py       # Custom exception handler
│   ├── health.py           # Health check endpoint
│   ├── logging_config.py   # Structured logging setup
│   ├── wsgi.py             # WSGI entrypoint for Gunicorn
│   └── asgi.py             # ASGI entrypoint (for future async)
├── accounts/        # App #1: Authentication & user management
│   ├── views.py            # Register, login, logout, me, token refresh
│   ├── serializers.py      # User/Register serializers + validation
│   ├── urls.py             # Auth route definitions
│   ├── tests.py            # Auth-specific tests
│   └── models.py           # (empty — uses Django's built-in User)
└── transactions/    # App #2: Core business logic
    ├── views.py            # TransactionViewSet (CRUD + summary)
    ├── models.py           # Transaction model with UUID PK
    ├── serializers.py      # Transaction serializer + validation
    ├── urls.py             # DRF router configuration
    ├── tests.py            # Comprehensive CRUD + summary tests
    └── admin.py            # Django admin configuration
```

**Why not one massive file?**

| Principle | How This Project Implements It |
|-----------|-------------------------------|
| **Separation of Concerns** | Auth logic lives in `accounts/`, money logic lives in `transactions/`. They share nothing except the User model FK. |
| **Django's App Pattern** | Each app is a self-contained module that can be reused in other Django projects. `accounts/` could be extracted into a shared auth library. |
| **Single Responsibility** | `authentication.py` does ONE thing: extract JWT from cookies. `exceptions.py` does ONE thing: format errors. `health.py` does ONE thing: probe DB and cache. |
| **Configuration vs Logic** | `config/` contains only wiring — no business logic. Settings are environment-driven via `python-decouple`, not hardcoded. |
| **Testability** | Each app has its own `tests.py`. Tests can be run in isolation: `pytest accounts/tests.py` or `pytest transactions/tests.py`. |

### 3.2 Design Patterns in Use

#### Pattern 1: Template Method (DRF ViewSets)

`TransactionViewSet` inherits from `ModelViewSet`, which provides `list()`, `create()`, `retrieve()`, `update()`, `partial_update()`, `destroy()`. We override only the hooks we need:

```python
def get_queryset(self):      # Hook: filter by user
def perform_create(self):    # Hook: set user FK + invalidate cache
def perform_update(self):    # Hook: invalidate cache
def perform_destroy(self):   # Hook: invalidate cache
```

The parent class defines the algorithm (validate → save → return), subclass defines the specifics. This is the **Template Method** pattern — the skeleton of the operation is fixed, but steps are customizable.

#### Pattern 2: Strategy (Authentication Classes)

DRF's `DEFAULT_AUTHENTICATION_CLASSES` is a **Strategy pattern**. The framework iterates through `[CookieJWTAuthentication]` and tries each one. Each class encapsulates a different auth strategy. Changing from Bearer-only to cookie-based auth required writing *one new class* — no view code changed.

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'config.authentication.CookieJWTAuthentication',  # ← Swap strategy here
    ],
}
```

#### Pattern 3: Chain of Responsibility (Middleware)

Django's middleware stack is a classic Chain of Responsibility. Each middleware can:
- Process the request (modify it, reject it)
- Pass it to the next middleware
- Process the response on the way back

The order matters: SecurityMiddleware must run first, CorsMiddleware must run before the view (to handle preflight), AuthenticationMiddleware must run before the view uses `request.user`.

#### Pattern 4: Cache-Aside (Summary Endpoint)

```
Application code controls the cache, not the framework:
  1. Check cache
  2. On miss: compute, store, return
  3. On write: explicitly invalidate

This is "cache-aside" — the application is aware of the cache and
manages it explicitly. Contrast with "read-through" where the cache
layer sits transparently between app and DB.
```

#### Pattern 5: Custom Exception Handler (Decorator-like)

`custom_exception_handler` wraps DRF's default handler to add:
1. Consistent JSON error shape: `{"error": {"code": "...", "message": "...", "details": {...}}}`
2. Structured logging with request context (method, path, user)
3. Human-readable error codes mapped from HTTP status codes

This is registered once in settings and applies to ALL views automatically — no per-view try/except blocks needed.

#### Pattern 6: Multi-Stage Build (Docker)

The Dockerfile uses a **builder pattern** to separate build-time dependencies from runtime:

```
Stage 1 (builder):
  - Has gcc, libpq-dev (needed to compile psycopg2)
  - pip install into /install prefix
  - Discarded after build

Stage 2 (production):
  - Only has libpq5 (runtime library, not dev headers)
  - Copies /install from builder
  - No compiler, no build tools
  - Runs as non-root user (appuser)
```

Result: smaller image, smaller attack surface, no accidental dev tools in production.

### 3.3 Why httpOnly Cookies Over localStorage

| Concern | localStorage JWT | httpOnly Cookie JWT |
|---------|-----------------|-------------------|
| **XSS token theft** | Trivial — `localStorage.getItem('token')` | Impossible — JS cannot read httpOnly cookies |
| **CSRF** | Not applicable (token sent via JS) | Needs SameSite=Strict/Lax (configured) |
| **Automatic expiry** | Custom code needed | Browser handles cookie expiry |
| **Cross-tab sharing** | Works (same origin localStorage) | Works (same origin cookies) |
| **Mobile/native clients** | Easy (read storage) | Harder (need cookie jar) |

The trade-off is clear: httpOnly cookies are superior for browser-based SPAs where XSS is the primary threat. The `SameSite=Strict` flag mitigates the CSRF concern. For API clients (curl, mobile apps), the fallback Bearer header in `CookieJWTAuthentication` keeps them working.

### 3.4 Why UUID PKs

```python
id = models.UUIDField(
    primary_key=True,
    default=uuid.uuid4,
    editable=False
)
```

**Three reasons:**

1. **Security (IDOR prevention)**: Sequential integer IDs (`/api/transactions/1/`, `/2/`, `/3/`) are trivially enumerable. An attacker who authenticates can walk through all IDs. UUIDs (`a1b2c3d4-...`) cannot be guessed.

2. **Scalability**: UUIDs are globally unique. If this monolith ever splits into microservices, or data is sharded across databases, UUID PKs won't collide. Auto-increment IDs would require coordination (sequences, distributed ID generators).

3. **Offline generation**: The client could generate UUIDs (e.g., for optimistic UI updates). With auto-increment, the DB must assign the ID.

**Trade-off**: UUIDs are larger (16 bytes vs 4-8 bytes for integers) and can fragment B-tree indexes. For a personal finance app with thousands (not billions) of rows, this is negligible.

### 3.5 Why DecimalField for Money

```python
amount = models.DecimalField(max_digits=12, decimal_places=2)
```

**The problem with FloatField**:

```python
>>> 0.1 + 0.2
0.30000000000000004  # IEEE 754 floating-point artifact
```

Financial calculations MUST be exact. `DecimalField` maps to:
- Python: `decimal.Decimal` (arbitrary-precision decimal arithmetic)
- SQL: `DECIMAL(12,2)` (fixed-point numeric type)
- PostgreSQL: `NUMERIC(12,2)` (exact storage, no rounding errors)

This matters when summing thousands of transactions or calculating balances — floating-point drift accumulates.

---

## 4. Translation for Operations

### 4.1 Service-to-Infrastructure Mapping

If you were deploying this on AWS (or any cloud provider), here's how each Docker Compose service maps to managed infrastructure:

| Docker Service | Cloud Equivalent | Why You'd Migrate |
|---------------|-----------------|-------------------|
| **`db` (PostgreSQL)** | **AWS RDS** / **GCP Cloud SQL** | Managed backups, automated minor version upgrades, read replicas for scaling, Multi-AZ for HA, point-in-time recovery. No more managing pg_dump cron jobs. |
| **`redis` (Redis)** | **AWS ElastiCache** / **GCP Memorystore** | Managed clustering, automatic failover, backup/restore. In-memory engine so node failure = data loss without replication — ElastiCache handles this. |
| **`backend` (Gunicorn)** | **AWS ECS Fargate** / **GCP Cloud Run** | Serverless containers — no EC2 instances to patch. Auto-scaling based on CPU/request count. Rolling deployments with health checks. |
| **`nginx` (Reverse Proxy)** | **AWS ALB** / **GCP Cloud Load Balancer** + **CloudFront** / **Cloud CDN** | Terminate TLS at the load balancer. CDN caches static assets at edge locations. ALB does path-based routing (`/api/*` → ECS, `/*` → S3+CloudFront). |
| **`frontend` (Static files)** | **AWS S3 + CloudFront** / **GCP Cloud Storage + Cloud CDN** | Static assets served from object storage with CDN. No server to maintain. Cache-Control headers for browser caching. |
| **`.env` (Secrets)** | **AWS Secrets Manager** / **GCP Secret Manager** | Secrets encrypted at rest with KMS. Automatic rotation policies. Audit trail of who accessed what. IAM-controlled access. |

### 4.2 Infrastructure Architecture (Hypothetical Production)

```
                           ┌──────────────┐
                           │  CloudFront   │ ← CDN (caches static assets globally)
                           │   (CDN)      │
                           └──────┬───────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
              ┌─────▼─────┐              ┌──────▼──────┐
              │  S3 Bucket │              │   ALB/NLB   │ ← TLS termination
              │  (Static)  │              │  (Public)   │    ACM certificate
              └────────────┘              └──────┬──────┘
                                                │
                                     ┌──────────┴──────────┐
                                     │  Path-based routing: │
                                     │  /api/* → ECS        │
                                     │  /admin/* → ECS      │
                                     └──────────┬──────────┘
                                                │
                              ┌─────────────────┴─────────────────┐
                              │          ECS Fargate              │
                              │     (Gunicorn + Django)           │
                              │     Auto-scaling: 2-8 tasks       │
                              │     CPU/Memory: 512/1024          │
                              └────────┬───────────────┬──────────┘
                                       │               │
                              ┌────────▼──────┐  ┌─────▼─────────┐
                              │  RDS PostgreSQL│  │  ElastiCache  │
                              │  Multi-AZ     │  │  Redis        │
                              │  db.r6g.large │  │  cache.r6g    │
                              └───────────────┘  └───────────────┘
```

### 4.3 Docker Compose → Cloud-Native Translation

| Docker Compose Pattern | Cloud-Native Equivalent |
|------------------------|------------------------|
| `depends_on: condition: service_healthy` | ECS `dependsOn` conditions in task definitions; health check grace periods |
| `restart: unless-stopped` | ECS service auto-healing: replaces failed tasks automatically |
| `volumes: postgres_data:` | RDS managed storage with automated snapshots (no volume management) |
| `volumes: static_files:` | EFS mount across ECS tasks, OR serve statics from S3 (preferred) |
| `healthcheck:` blocks | ALB target group health checks (`/api/health/`) + ECS container health checks |
| `build: context:` | ECR repository + CodeBuild pipeline for image building |
| `environment:` vars | ECS task definition environment variables, sourced from Secrets Manager |
| `ports: "80:80"` | ALB listener on port 443 → forwards to ECS target group on port 8000 |

### 4.4 The Health Check Endpoint

```python
def health_check(request):
    health = {'status': 'healthy', 'db': 'ok', 'cache': 'ok'}
    # Tests DB: connection.ensure_connection()
    # Tests Cache: cache.set('health_check', 'ok', 10) + read-back
    return JsonResponse(health, status=200 or 503)
```

**What consumes this:**

1. **Docker HEALTHCHECK** (in Dockerfile): `curl http://localhost:8000/api/health/` every 30s. If it fails 3 times, Docker marks the container as unhealthy. Docker Compose can restart it.
2. **ALB Target Group Health Checks**: The load balancer pings `/api/health/` every 30s. Unhealthy targets are drained from the pool.
3. **Kubernetes liveness/readiness probes**: Same pattern — `/api/health/` serves both. Liveness: "kill and restart if this fails." Readiness: "stop sending traffic if cache is down but DB is up."

**Why it checks both DB and cache**: If Redis is down but PostgreSQL is up, the app is *degraded* (summary endpoint will be slower) but still functional. A health check that only tests DB would report "healthy" and traffic would keep flowing, but users would experience timeouts on cache-dependent endpoints. By checking both, you can tune probe sensitivity — readiness can fail on Redis while liveness only fails on DB.

### 4.5 Container Startup Sequence

```
docker compose up
  │
  ├─► db (PostgreSQL) starts
  │     └─► healthcheck: pg_isready -U mm_user -d money_manager
  │         └─► Reports healthy after ~5-10 seconds
  │
  ├─► redis starts
  │     └─► healthcheck: redis-cli ping
  │         └─► Reports healthy after ~1-2 seconds
  │
  ├─► backend WAITS for db: healthy AND redis: healthy
  │     └─► entrypoint.sh:
  │           1. Wait loop: TCP socket check on DB_HOST:DB_PORT
  │              → Ensures PostgreSQL is accepting connections
  │              → (Not just container started, but DB ready)
  │           2. python manage.py migrate --noinput
  │              → Applies pending migrations (idempotent)
  │           3. python manage.py collectstatic --noinput
  │              → Gathers static files into /app/staticfiles/
  │           4. exec gunicorn config.wsgi:application
  │              → Replaces shell process with Gunicorn (PID 1)
  │     └─► healthcheck: curl http://localhost:8000/api/health/
  │         └─► Reports healthy after Gunicorn is ready
  │
  └─► nginx starts AFTER backend (depends_on)
        └─► Serves on port 80
        └─► Routes /api/ → backend:8000
        └─► Routes / → /usr/share/nginx/html (frontend static)
```

**Why `exec` in entrypoint.sh**: `exec "$@"` replaces the shell process with Gunicorn. This means Gunicorn becomes PID 1 in the container, and it receives OS signals (SIGTERM for graceful shutdown) directly. Without `exec`, the shell would be PID 1, Gunicorn would be a child process, and signals might not propagate correctly — leading to forced kills after timeout.

### 4.6 Logging & Observability

```python
# logging_config.py — structured logging ready for log aggregation
LOGGING_CONFIG = {
    'formatters': {
        'verbose': {  # Human-readable for dev
            'format': '{asctime} [{levelname}] {name} | {message}',
        },
        'json': {     # Machine-parseable for production (ELK/Loki)
            'format': '{asctime} {levelname} {name} {message}',
        },
    },
    'loggers': {
        'transactions': {'level': 'INFO', ...},  # All CRUD operations logged
        'accounts': {'level': 'INFO', ...},       # Login/register/logout logged
        'django.request': {'level': 'ERROR', ...}, # Only 4xx/5xx errors
    },
}
```

**Operations perspective**: In production, you'd switch the handler from `console` (stdout, collected by Docker/CloudWatch) to a JSON formatter that can be parsed by log aggregation tools (Elasticsearch, Loki, Datadog). The structured log format with `{asctime} {levelname} {name} {message}` is already parseable by most log shippers.

---

## 5. Security Architecture

### 5.1 httpOnly Cookie-Based JWT Authentication

#### Problem Solved
Traditional localStorage-based JWT storage is vulnerable to XSS attacks:
```javascript
// Vulnerable pattern:
const token = localStorage.getItem('access_token');  // Attacker can steal this
```

#### Solution Implemented
HttpOnly cookies are browser-managed and inaccessible to JavaScript:
```javascript
// Secure pattern:
// Browser automatically sends cookie, application cannot access it
fetch('/api/transactions/', { credentials: 'include' });
// Cookies included automatically, cannot be stolen by JS
```

#### Implementation Details

**Backend Authentication Class (`config/authentication.py`):**
```python
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Step 1: Try to extract token from httpOnly cookie
        access_token = request.COOKIES.get('access_token')
        
        if not access_token:
            # Step 2: Fallback to Bearer token in Authorization header
            # This allows API testing tools (Postman, curl) to still work
            auth_header = self.get_header(request)  
        
        # Step 3: Validate token (SimpleJWT handles this)
        return (user, None)  # Returns (user, None) tuple
```

**Setting Cookies (`accounts/views.py`):**
```python
def _set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        key='access_token',
        value=str(access_token),
        max_age=60 * 60 * 24,              # 1 day
        httponly=settings.HTTPONLY_COOKIES_ENABLED,  # True in prod, False in dev
        secure=settings.SECURE_COOKIE_ENABLED,       # True on HTTPS, False on HTTP
        samesite='Strict' if settings.SECURE_COOKIE_ENABLED else 'Lax',
        path='/',
    )
    # Refresh token cookie (7 days)...
```

#### Environment-Based Configuration

The `HTTPONLY_COOKIES_ENABLED` setting is environment-aware:

| Environment | DEBUG | HTTPONLY_COOKIES_ENABLED | SECURE_COOKIE_ENABLED | Use Case |
|-------------|-------|-------------------------|----------------------|----------|
| Development | True | False | False | Local debugging, DevTools inspection |
| Staging | False | True | False | Testing with HTTP (self-signed cert) |
| Production | False | True | True | Live environment with HTTPS |
| Testing | False | False | False | Unit/integration tests |

**In `config/settings.py`:**
```python
HTTPONLY_COOKIES_ENABLED = config(
    'HTTPONLY_COOKIES_ENABLED', 
    default=not DEBUG,  # Automatically True when DEBUG=False
    cast=bool
)
```

#### CORS Configuration for Cookie Auth

Cookie-based auth requires explicit CORS configuration:
```python
# config/settings.py
CORS_ALLOW_CREDENTIALS = True  # CRITICAL: Allow credentials in CORS requests
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost,http://127.0.0.1',
    cast=Csv()
)
```

**Frontend Configuration:**
```javascript
// frontend/js/app.js
fetch('/api/auth/me/', {
    method: 'GET',
    credentials: 'include',  // CRITICAL: Include cookies in request
})
```

Without `credentials: 'include'`, the browser will NOT send cookies automatically.

#### Cookie Lifecycle

```
1. User login: POST /api/auth/login/
   └─ Backend validates credentials
   └─ Generates access_token (1 day) and refresh_token (7 days)
   └─ Sets both in httpOnly cookies with Set-Cookie headers
   └─ Browser stores cookies automatically

2. Subsequent requests: GET /api/transactions/
   └─ Browser automatically includes cookies (due to credentials: 'include')
   └─ Backend's CookieJWTAuthentication extracts token from request.COOKIES
   └─ SimpleJWT validates the token
   └─ Request proceeds with user context

3. Access token expiry (after 1 day):
   └─ Frontend detects 401 response
   └─ Frontend calls POST /api/auth/token/refresh/
   └─ Backend uses refresh_token from cookie to issue new access_token
   └─ Sets new access_token in cookie
   └─ User session continues seamlessly

4. Refresh token expiry (after 7 days):
   └─ Backend rejects refresh request (refresh_token expired)
   └─ Frontend redirects to login page
   └─ User must login again

5. Logout: POST /api/auth/logout/
   └─ Backend clears both cookies (max_age=0)
   └─ Browser deletes cookies
   └─ User logged out completely
```

#### Security Properties

| Threat | Protection |
|--------|------------|
| **XSS (JavaScript injection)** | httpOnly flag prevents JS access; cookie cannot be stolen |
| **CSRF (Cross-Site Request Forgery)** | SameSite=Strict prevents cookie transmission on cross-site requests |
| **Session Hijacking (MITM)** | Secure flag ensures HTTPS-only transmission |
| **Token Theft via Network Sniffer** | HTTPS encryption protects token in transit |
| **Long-lived Token Abuse** | Short access_token (1 day) limits exposure window |
| **Refresh Token Reuse** | Refresh token rotation (enabled) invalidates token after first use |

### 5.2

### 5.1 Defense-in-Depth Layers

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: Network                                         │
│   - Nginx as reverse proxy (not exposing Gunicorn)       │
│   - CORS whitelist (only configured origins)              │
│   - In production: TLS termination at ALB/Nginx          │
├─────────────────────────────────────────────────────────┤
│ LAYER 2: Transport                                       │
│   - httpOnly cookies (JS-inaccessible)                   │
│   - Secure flag (HTTPS-only) in production               │
│   - SameSite=Strict (CSRF protection) in production      │
│   - SameSite=Lax (reasonable) in development             │
├─────────────────────────────────────────────────────────┤
│ LAYER 3: Authentication                                  │
│   - JWT with HMAC signing (SECRET_KEY)                   │
│   - Short-lived access token (1 day)                     │
│   - Refresh token rotation (stolen token → useless)      │
│   - Rate limiting: 5/min on login (brute-force)          │
├─────────────────────────────────────────────────────────┤
│ LAYER 4: Authorization                                   │
│   - User-scoped querysets (IsAuthenticated + filter)     │
│   - UUID PKs (IDOR prevention via non-guessability)     │
│   - Permission classes per-viewset                       │
├─────────────────────────────────────────────────────────┤
│ LAYER 5: Data                                            │
│   - Django ORM parameterized queries (SQL injection)     │
│   - Serializer validation (amount > 0, valid choices)    │
│   - Password hashing: PBKDF2 (Django default)            │
│   - Non-root Docker user (appuser)                       │
├─────────────────────────────────────────────────────────┤
│ LAYER 6: Operations                                      │
│   - .env excluded from git (secrets in env)              │
│   - Multi-stage Docker (no build tools in prod)          │
│   - DEBUG=False in production (no stack traces)          │
│   - Health checks (auto-restart unhealthy containers)   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 JWT Threat Model

| Threat | Mitigation |
|--------|-----------|
| **Token theft via XSS** | httpOnly cookie — JS cannot read it |
| **Token theft via MITM** | HTTPS (Secure cookie flag) + HSTS |
| **Token theft via CSRF** | SameSite=Strict cookie |
| **Brute-force login** | Rate limiting (5/min per IP) via `LoginRateThrottle` |
| **Refresh token replay** | Rotation enabled — each refresh issues new refresh token, old one invalidated |
| **IDOR (guessing IDs)** | UUID PKs — unguessable, 2^122 random bits |

---

## 6. Testing Strategy

### 6.1 Test Architecture

```
backend/
├── conftest.py              ← Global fixtures (disable throttling)
├── accounts/tests.py        ← Auth tests (register, login, me, logout, cookies)
└── transactions/tests.py    ← CRUD + summary + filtering + isolation tests
```

**Global fixture** (`conftest.py`):

```python
@pytest.fixture(autouse=True)
def disable_throttle(monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, 'allow_request', lambda self, request, view: True)
```

This prevents tests from hitting rate limits. It's an **autouse** fixture, meaning every test gets it. Clean pattern — tests focus on business logic, not on working around throttling.

**Test organization**: Each test class maps to an HTTP method or concept:
- `TestTransactionCreate` → POST /api/transactions/
- `TestTransactionRead` → GET /api/transactions/ + filtering
- `TestTransactionUpdate` → PUT + PATCH
- `TestTransactionDelete` → DELETE
- `TestTransactionSummary` → GET /api/transactions/summary/
- `TestAuthRegistration` → POST /api/auth/register/
- `TestAuthLogin` → POST /api/auth/login/
- `TestAuthMeEndpoint` → GET /api/auth/me/
- `TestAuthLogout` → POST /api/auth/logout/

### 6.2 What's Covered

| Test Area | Specific Tests |
|-----------|---------------|
| **Happy path** | Valid create, valid login, valid summary calculations |
| **Validation** | Negative amount, invalid category, missing fields, invalid email |
| **Auth** | Unauthenticated requests → 401, cookie presence checks (httponly flag) |
| **User isolation** | User A cannot see User B's transactions, 404 for other user's data |
| **Filter** | Status filter, category filter |
| **Partial update** | PATCH only changes specified fields |
| **Deletion** | Object removed from DB after DELETE |
| **Summary math** | Exact arithmetic: 150.00 spent + 5000.00 credited = 4850.00 balance |
| **Summary breakdown** | Only spent transactions appear in category_breakdown (credited excluded) |

**Coverage gate**: `--cov-fail-under=80` in CI. This means the pipeline fails if coverage drops below 80%.

### 6.3 CI Pipeline (from ci.yml)

```
Push to any branch →
  1. Setup Python 3.12
  2. Install requirements-dev.txt (pytest, flake8, factory-boy)
  3. flake8 backend/  → Check code style
  4. pytest --cov --cov-fail-under=80  → Run tests with coverage gate
  5. docker build → Verify Docker image builds cleanly
```

---

## 7. Interview Talking Points

### 🎯 "Walk me through the architecture of this project"

> "This is a full-stack personal finance tracker. The backend is Django with Django REST Framework, using a custom JWT authentication class that extracts tokens from httpOnly cookies instead of localStorage. The frontend is vanilla JavaScript — intentionally framework-free to demonstrate DOM fundamentals. The infrastructure is Docker Compose with four services: Nginx reverse proxy, Django+Gunicorn, PostgreSQL 16, and Redis 7 for caching. It uses a multi-stage Docker build with a non-root user, has a health check endpoint that probes both DB and cache, uses the cache-aside pattern for the summary aggregation endpoint, and follows Django's app pattern with clean separation between accounts and transactions."

### 🎯 "Why httpOnly cookies instead of localStorage?"

> "XSS prevention. If an attacker injects JavaScript into the page, `localStorage.getItem('token')` returns the JWT. httpOnly cookies are invisible to JavaScript — the browser sends them but code can't read them. The cost is slightly more complex CSRF handling, which we address with `SameSite=Strict` on cookies. We also kept a Bearer header fallback in `CookieJWTAuthentication` so API clients and testing tools still work."

### 🎯 "Why UUID primary keys?"

> "Three reasons. Security — prevents IDOR via sequential ID enumeration. Scalability — UUIDs are globally unique, so if this monolith ever splits into microservices, PKs won't collide. And they enable offline ID generation if we add optimistic UI. The trade-off is larger index size, but for a personal finance app with thousands of rows, that's negligible."

### 🎯 "Why DecimalField instead of FloatField for money?"

> "IEEE 754 floating point produces rounding errors like `0.1 + 0.2 = 0.30000000000000004`. Financial calculations require exact decimal arithmetic. `DecimalField` maps to Python's `Decimal` type and SQL's `DECIMAL/NUMERIC` — fixed-point, no rounding, exact up to the specified precision. This is non-negotiable for any system handling money."

### 🎯 "How does caching work?"

> "Cache-aside pattern on the summary endpoint. We use Redis with a per-user cache key — `summary_{user_id}`. On read, we check Redis first; on miss, we run the aggregation queries (SUM spent, SUM credited, GROUP BY category), store the result in Redis with a 5-minute TTL, and return. On every write — create, update, delete — we explicitly invalidate that user's cache key. No stale reads because invalidation is synchronous with the write. Per-user keys prevent User A's writes from invalidating User B's cache."

### 🎯 "How does authentication work end-to-end?"

> "On login, the backend issues a JWT access token (1-day TTL) and refresh token (7-day TTL), both set as httpOnly cookies with `Secure` and `SameSite` flags. Every subsequent API call uses `credentials: 'include'` — the browser automatically sends the cookies. Our custom `CookieJWTAuthentication` extracts the access token from the cookie, validates it via SimpleJWT, and sets `request.user`. If the access token expires, the frontend's `authFetch()` wrapper catches the 401, calls the refresh endpoint (which reads the refresh cookie), gets a new access token cookie in the response, and retries the original request — all transparent to the user. Refresh tokens are rotated on each use, so a stolen refresh token becomes invalid after the legitimate user refreshes once."

### 🎯 "How would this scale?"

> "The current bottleneck is the synchronous Django/Gunicorn layer — 3 workers handle 3 concurrent requests. To scale horizontally: put Gunicorn behind an ALB, run multiple ECS Fargate tasks, let the ALB distribute requests. PostgreSQL scales vertically first (bigger RDS instance), then via read replicas for read-heavy workloads. Redis scales via ElastiCache cluster mode. Static assets move to S3 + CloudFront — no reason for Nginx to serve them. For the summary endpoint specifically, if the 5-minute cache TTL isn't enough, we could add database-level materialized views refreshed on a cron, or move aggregation to a read replica."

### 🎯 "What would you change before production?"

> "Enable HTTPS everywhere — `SECURE_COOKIE_ENABLED=True`, `SECURE_SSL_REDIRECT=True`, HSTS headers. Move secrets out of docker-compose.yml into AWS Secrets Manager or at least a `.env` file that's never committed. Add structured JSON logging for a log aggregation pipeline. Add a proper connection pool (PgBouncer) between Gunicorn and PostgreSQL — without it, each Gunicorn worker opens its own connection, which doesn't scale. And add a CSP header via Nginx to further mitigate XSS."

---

## Appendix: Quick Reference

### Port Map

| Service | Container Port | Host Port | Purpose |
|---------|---------------|-----------|---------|
| Nginx | 80 | 80 | Frontend + reverse proxy |
| Django/Gunicorn | 8000 | 8000 | API server |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Cache |

### Environment Variables by Category

| Category | Variables |
|----------|----------|
| **Django Core** | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` |
| **Database** | `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| **CORS** | `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ALL_ORIGINS` |
| **Redis** | `REDIS_URL` |
| **Cookie Security** | `SECURE_COOKIE_ENABLED`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS` |
| **Logging** | `LOG_LEVEL` |

### Key Files and Their Roles

| File | Role |
|------|------|
| `config/settings.py` | Single source of truth for ALL configuration. Environment-driven via `python-decouple`. |
| `config/authentication.py` | Custom JWT class that bridges httpOnly cookies to DRF's auth system. |
| `config/exceptions.py` | Consistent JSON error format across all endpoints + structured logging. |
| `config/health.py` | Health probe consumed by Docker HEALTHCHECK and load balancer target groups. |
| `apps/transactions/views.py` | Core business logic: CRUD, user-scoped queries, cache-aside summary, cache invalidation. |
| `apps/transactions/models.py` | Data schema: UUID PK, DecimalField for money, composite indexes for query patterns. |
| `apps/accounts/views.py` | Auth flow: register, login, logout, token refresh — all cookie-based. |
| `docker-compose.yml` | Full-stack orchestration with health checks, dependency ordering, and persistent volumes. |
| `backend/Dockerfile` | Multi-stage build: separate compile and runtime stages, non-root user, health check. |
| `nginx/nginx.conf` | Reverse proxy config: route `/api/*` and `/admin/*` to Gunicorn, serve frontend statics. |
| `backend/entrypoint.sh` | Container startup: wait for DB, run migrations, collect static, launch Gunicorn with `exec`. |
