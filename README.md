# 💰 Money Manager

A modern, full-stack money management application with **user authentication** to track income and expenses with a clean, responsive UI.

Built with **Django REST Framework** (backend), **JWT Authentication**, and **Vanilla JavaScript** (frontend).

![Dashboard](https://img.shields.io/badge/Status-Active-22c55e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x+-092e20?style=flat-square&logo=django&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT-f59e0b?style=flat-square&logo=jsonwebtokens&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)

---

## ✨ Features

- **🔐 User Authentication** — Register & login with JWT tokens (access + refresh)
- **👤 Multi-User Support** — Each user sees only their own transactions
- **💳 Transaction Tracking** — Record income and expenses with amount, category, status, date, and description
- **📊 Dashboard & Analytics** — Summary cards and an interactive Chart.js doughnut chart for visual expense breakdown
- **🏷️ Category System** — 10 built-in categories with emoji icons (Food, Transport, Shopping, Bills, Health, Entertainment, Salary, Freelance, Investment, Other)
- **🔍 Filters** — Filter transactions by status (Income/Expense) and category
- **🌙 Dark/Light Mode** — Theme toggle with localStorage persistence
- **📱 Responsive Design** — Works seamlessly on desktop, tablet, and mobile
- **🛡️ Django Admin** — Built-in admin panel for advanced data management
- **🔄 REST API** — Clean RESTful API with full CRUD operations

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x + Django REST Framework |
| **Authentication** | SimpleJWT (access + refresh tokens) |
| **Frontend** | HTML5 + Vanilla CSS + JavaScript |
| **Database** | SQLite (dev) → PostgreSQL (production) |
| **API** | RESTful JSON API |
| **Design** | Dark-mode-first, Glassmorphism, Inter font |

---

## 📁 Project Structure

```
MoneyManager/
├── backend/                    # Django project
│   ├── manage.py
│   ├── config/                 # Project settings
│   │   ├── settings.py         # DRF, JWT, CORS config
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── accounts/               # Auth app (Phase 2)
│   │   ├── serializers.py      # Register & user serializers
│   │   ├── views.py            # Register, login, profile views
│   │   └── urls.py             # Auth URL routing
│   ├── transactions/           # Main app
│   │   ├── models.py           # Transaction model (UUID PK + User FK)
│   │   ├── serializers.py      # DRF serializers + validation
│   │   ├── views.py            # API ViewSet (user-scoped) + summary
│   │   ├── urls.py             # DRF router
│   │   └── admin.py            # Admin panel config
│   └── requirements.txt
├── frontend/                   # Static frontend
│   ├── index.html              # Main app (requires auth)
│   ├── login.html              # Login/Register page
│   ├── css/
│   │   ├── styles.css          # Design system
│   │   └── auth.css            # Auth page styles
│   └── js/
│       ├── app.js              # Main app logic (with JWT)
│       └── auth.js             # Login/register logic
├── README.md
└── money_manager_deep_dive.md  # Technical deep dive
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/Sunil2409/money-management-system.git
cd money-management-system
```

### 2. Set up the backend

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
cd backend
python manage.py migrate

# Start the backend server
python manage.py runserver 8000
```

### 3. Serve the frontend

Open a new terminal:

```bash
cd frontend
python3 -m http.server 5500
```

### 4. Open the app

Navigate to **http://127.0.0.1:5500** in your browser.
You'll be redirected to the **login page** — create an account to get started!

---

## 🔐 Authentication Flow

```
Register/Login → JWT tokens issued → Stored in localStorage
→ Every API request includes Authorization: Bearer <token>
→ Token expires (1 day) → Auto-refresh with refresh token (7 days)
→ Logout clears tokens → Redirects to login
```

| Step | What Happens |
|------|-------------|
| **Register** | `POST /api/auth/register/` → Creates user → Returns JWT tokens |
| **Login** | `POST /api/auth/login/` → Validates credentials → Returns JWT tokens |
| **API Calls** | Every `fetch()` includes `Authorization: Bearer <access_token>` |
| **Token Refresh** | On 401 → auto-POST to `/api/auth/token/refresh/` with refresh token |
| **Logout** | Clears `localStorage` tokens → Redirects to `login.html` |

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register/` | Create a new account |
| `POST` | `/api/auth/login/` | Get JWT access + refresh tokens |
| `POST` | `/api/auth/token/refresh/` | Refresh expired access token |
| `GET` | `/api/auth/me/` | Get current user profile |

### Transactions (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transactions/` | List user's transactions |
| `POST` | `/api/transactions/` | Create a new transaction |
| `GET` | `/api/transactions/{id}/` | Retrieve a transaction |
| `PUT` | `/api/transactions/{id}/` | Update a transaction |
| `DELETE` | `/api/transactions/{id}/` | Delete a transaction |
| `GET` | `/api/transactions/summary/` | Get spending summary & stats |

### Query Parameters (GET /api/transactions/)

| Parameter | Values | Description |
|-----------|--------|-------------|
| `status` | `spent`, `credited` | Filter by transaction status |
| `category` | `food`, `transport`, `shopping`, `bills`, `health`, `entertainment`, `salary`, `freelance`, `investment`, `other` | Filter by category |

### Example: Authenticated Request

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "sunil", "email": "sunil@test.com", "password": "test1234"}'

# Create transaction with token
curl -X POST http://127.0.0.1:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-access-token>" \
  -d '{"amount": "250.00", "category": "food", "status": "spent", "description": "Lunch", "date": "2026-05-02"}'
```

---

## 🔄 Data Flow

```
User fills form → JavaScript collects data → authFetch() adds JWT header
→ fetch() POST to /api/transactions/ → Django validates token
→ DRF Serializer validates data → ORM saves to SQLite (with user FK)
→ JSON response → JavaScript updates DOM → Dashboard refreshes
```

---

## 🗺️ Roadmap

- [x] Phase 1 — Core CRUD + Responsive UI
- [x] Phase 2 — User Authentication (JWT)
- [x] Phase 3 — Dashboard Charts (Chart.js)
- [ ] Phase 4 — AI-powered Categorization
- [ ] Phase 5 — AWS Deployment (ECS + RDS + S3 + CloudFront)
- [ ] Phase 6 — Budget Alerts & Recurring Transactions

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Sunil Kumar E**

---

<p align="center">Built with ❤️ using Django & JavaScript</p>
