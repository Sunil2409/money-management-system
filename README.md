# 💰 Money Manager

A modern, full-stack money management application to track income and expenses with a clean, responsive UI.

Built with **Django REST Framework** (backend) and **Vanilla JavaScript** (frontend).

![Dashboard](https://img.shields.io/badge/Status-Active-22c55e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x+-092e20?style=flat-square&logo=django&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-6366f1?style=flat-square)

---

## ✨ Features

- **Transaction Tracking** — Record income and expenses with amount, category, status, date, and description
- **Dashboard** — Summary cards showing total income, expenses, net balance, and transaction count
- **Category System** — 10 built-in categories with emoji icons (Food, Transport, Shopping, Bills, Health, Entertainment, Salary, Freelance, Investment, Other)
- **Filters** — Filter transactions by status (Income/Expense) and category
- **Dark/Light Mode** — Theme toggle with localStorage persistence
- **Responsive Design** — Works seamlessly on desktop, tablet, and mobile
- **Django Admin** — Built-in admin panel for advanced data management
- **REST API** — Clean RESTful API with full CRUD operations

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x + Django REST Framework |
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
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── transactions/           # Main app
│   │   ├── models.py           # Transaction model (UUID PK)
│   │   ├── serializers.py      # DRF serializers + validation
│   │   ├── views.py            # API ViewSet + summary endpoint
│   │   ├── urls.py             # DRF router
│   │   └── admin.py            # Admin panel config
│   └── requirements.txt
├── frontend/                   # Static frontend
│   ├── index.html
│   ├── css/
│   │   └── styles.css          # Design system with CSS variables
│   └── js/
│       └── app.js              # API integration & UI logic
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/MoneyManager.git
cd MoneyManager
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

# Create admin user (optional)
python manage.py createsuperuser

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

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transactions/` | List all transactions |
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

### Example: Create a Transaction

```bash
curl -X POST http://127.0.0.1:8000/api/transactions/ \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "250.00",
    "category": "food",
    "status": "spent",
    "description": "Lunch at office canteen",
    "date": "2026-05-01"
  }'
```

---

## 🔄 Data Flow

```
User fills form → JavaScript collects data → fetch() POST to /api/transactions/
→ Django DRF Serializer validates → ORM saves to SQLite
→ JSON response → JavaScript updates DOM → User sees dashboard updated
```

---

## 🗺️ Roadmap

- [x] Phase 1 — Core CRUD + Responsive UI
- [ ] Phase 2 — User Authentication (Django auth)
- [ ] Phase 3 — Dashboard Charts (Chart.js)
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
