# 💳 Cloud-Native Money Manager & FinOps Ledger

[![Production CI/CD Pipeline](https://github.com/Sunil2409/money-management-system/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/Sunil2409/money-management-system/actions/workflows/deploy.yml)
[![AWS Free Tier](https://img.shields.io/badge/AWS%20Spend-%240.00%2Fmonth-brightgreen.svg?logo=amazon-aws)](https://aws.amazon.com/free/)
[![Terraform 1.10+](https://img.shields.io/badge/IaC-Terraform%201.10%2B-623CE4.svg?logo=terraform)](https://www.terraform.io/)
[![Zero-SSH](https://img.shields.io/badge/Security-Zero--SSH%20%7C%20AWS%20SSM-blueviolet.svg)](https://aws.amazon.com/systems-manager/)
[![OIDC Keyless](https://img.shields.io/badge/Auth-AWS%20OIDC%20Keyless-orange.svg)](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A production-engineered, cost-optimized financial ledger designed for zero-downtime deployment on the **AWS Free Tier ($0.00/month)**.

Engineered with **Terraform (IaC)**, keyless **AWS IAM OIDC** GitHub Actions CI/CD, automated **Trivy / Bandit DevSecOps** barriers, asynchronous **Celery worker** streaming pipelines, and **AWS Systems Manager (SSM) zero-SSH** container orchestration.

---

## 🌐 Live Production Deployment

| Service | Endpoint | Status | Description |
|---|---|---|---|
| **Web Application** | [http://13.233.86.78/](http://13.233.86.78/) | `HTTP 200 OK` | Production Vanilla JS SPA Dashboard |
| **User Authentication** | [http://13.233.86.78/login.html](http://13.233.86.78/login.html) | `HTTP 200 OK` | HttpOnly Cookie JWT Auth & Registration |
| **API Health Check** | [http://13.233.86.78/api/health/](http://13.233.86.78/api/health/) | `HTTP 200 OK` | Active PostgreSQL & Redis Probes |
| **Swagger OpenAPI Docs** | [http://13.233.86.78/api/docs/](http://13.233.86.78/api/docs/) | `HTTP 200 OK` | Interactive REST API Documentation |

---

## 🏛️ System Architecture

```text
                             [ GitHub Actions CI/CD ]
                                        │
                         (1) Keyless OIDC Authentication
                                        ▼
    ┌─────────────────────────── [ AWS Cloud ] ───────────────────────────┐
    │                                                                     │
    │  [ Amazon ECR ] ◄── Push Immutable SHA Image (Post-Trivy Scan)     │
    │                                                                     │
    │  [ AWS SSM Parameter Store ] ──► (Runtime Decrypted Secrets)        │
    │                                                                     │
    │  [ AWS Systems Manager ] ──────► Dispatches Run Command (Zero-SSH) │
    │                                         │                           │
    │  ┌── VPC (10.0.0.0/16) ─────────────────┼────────────────────────┐  │
    │  │                                      ▼                        │  │
    │  │  ┌── EC2 t3.micro Host (1GB RAM + 2GB Swapfile on EBS) ────┐  │  │
    │  │  │                                                         │  │  │
    │  │  │  [ Nginx:1.25 ] (Port 80 Ingress, Rate Limiting, Proxy) │  │  │
    │  │  │            │                                            │  │  │
    │  │  │            ├──► [ Django API (Gunicorn 2w+2t) ] (220M)  │  │  │
    │  │  │            │          │                                 │  │  │
    │  │  │            │          ├─► [ PostgreSQL 16 ] (140M)      │  │  │
    │  │  │            │          └─► [ Redis 7 Cache/Queue ] (64M) │  │  │
    │  │  │            │                    ▲                       │  │  │
    │  │  │            └────────────────────┼───────────────────────┤  │  │
    │  │  │                                 ▼                       │  │  │
    │  │  │  [ Celery Worker + Beat ] (Combined Mode: 160M)         │  │  │
    │  │  │            │                                            │  │  │
    │  │  └────────────┼────────────────────────────────────────────┘  │  │
    │  │               │                                               │  │
    │  │               ▼                                               │  │
    │  │     (S3 Gateway Endpoint) ──► [ Encrypted Private S3 Bucket ] │  │
    │  │                                 • AES-256 Server-Side Encrypt │  │
    │  │                                 • 90-Day Glacier IR Transition│  │
    │  │                                 • 15-Min Presigned URLs Only  │  │
    │  │  └────────────────────────────────────────────────────────────┘  │
    │  │                                                                  │
    │  │  [ AWS Budgets ] ──► Hard Alert at $1.00 USD Spend Threshold     │
    │  └──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key DevOps & Systems Engineering Highlights

### 1. Zero-SSH GitOps Continuous Deployment
- **AWS Systems Manager (SSM) Run Command**: Zero long-lived SSH daemon keys on the server (`port 22` ingress is completely bypassed for CI/CD). GitHub Actions targets running instances by AWS resource tags (`Project=MoneyManager`) using dynamic document execution.
- **S3 Atomic Manifest Synchronization**: Docker manifests, Nginx configurations, and frontend assets are compressed and synchronized through an encrypted S3 bucket pipeline directly into `/opt/moneymanager`.
- **Dynamic Host Upstream DNS Refresh**: Automated Nginx refresh prevents stale internal Docker bridge IP caching (eliminating HTTP 502 Bad Gateway during rolling container recreation).
- **Automated Rollback & Readiness Probes**: Deployment scripts actively poll `/api/health/` verifying active PostgreSQL queries and Redis read/write cycles before exiting.

### 2. Supply Chain Security & DevSecOps
- **Keyless AWS Authentication (OIDC)**: Eliminates static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` secrets from GitHub. Runners authenticate directly through AWS STS using short-lived tokens restricted to the repository's cryptographic sub-claim (`repo:Sunil2409/money-management-system:*`).
- **Static Application Security Testing (SAST)**: Automated **Bandit** AST security scanning blocks dangerous function execution and unsafe deserialization.
- **Container Vulnerability Auditing**: Integrated **Trivy** vulnerability scanning automatically fails CI builds upon detecting unpatched `HIGH` or `CRITICAL` CVEs.
- **Quality Enforcement**: Automated **PyTest** suite enforcing an **80%+ code coverage gate** with 30 unit tests across authentication and transactional domains.

### 3. FinOps & Low-Memory Linux Engineering ($0.00/Month)
- **100% Free Tier Compliance**:
  - **Compute**: Single `t3.micro` instance (750 hours/month Free Tier allocation).
  - **Storage**: 15 GB encrypted `gp3` root EBS (safely within the 30 GB monthly account limit).
  - **Networking**: Leverages an **S3 Gateway VPC Endpoint** (100% free) avoiding costly NAT Gateways (~$32+/month).
  - **Budget Safety**: An `aws_budgets_budget` sends automated SNS/email alerts if actual or forecasted spend exceeds **$1.00 USD**.
- **2 GB Linux EBS Swap Buffer**: Deployed via Terraform `user_data` bootstrap with `vm.swappiness=10` and `vm.vfs_cache_pressure=50`, expanding addressable virtual memory to 3 GB and preventing Linux Out-Of-Memory (OOM) killer terminations.
- **Hard Container Memory Limits**: Docker memory limits (`mem_limit`) and reservations maintain total concurrent RAM consumption under 620 MB:
  - `nginx`: 32 MB
  - `db` (PostgreSQL 16): 140 MB (`shared_buffers=32MB`, `max_connections=30`)
  - `redis` (Redis 7): 64 MB (`maxmemory 48mb`, `allkeys-lru`)
  - `backend` (Django + Gunicorn): 220 MB
  - `celery_worker` (Worker + Beat): 160 MB

### 4. Asynchronous Event-Driven Architecture
- **Combined Celery Worker & Beat Engine**: Executes both scheduled periodic tasks and asynchronous job queues in a single low-memory Python process (`--beat --concurrency=1`).
- **Non-Blocking In-Memory PDF Generation Pipeline**:
  - Monthly financial account statements are generated in memory using **ReportLab** without intermediate disk I/O bottlenecks.
  - Uploads stream directly to a private, encrypted S3 bucket using `boto3`.
  - Multi-tenant authorization generates time-limited (**15-minute**) Presigned S3 URLs—completely shielding the S3 bucket from public read access.
- **Lifecycle Data Tiering**: S3 objects automatically transition to **Glacier Instant Retrieval** after 90 days and expire after 365 days.

---

## 🛠️ Technology Stack

| Layer | Tools & Technologies |
|---|---|
| **Infrastructure as Code** | Terraform 1.10+ (Modular, S3 Native State Locking) |
| **Cloud Provider** | AWS (EC2, S3, ECR, VPC, IAM, SSM Parameter Store, Systems Manager, Budgets) |
| **CI/CD & Security** | GitHub Actions, AWS OIDC, Trivy, Bandit, Flake8, PyTest-Cov |
| **Containers & Runtime** | Docker Engine 29, Docker Compose V2, Alpine Linux, Nginx 1.25 |
| **Backend & Workers** | Python 3.12, Django 5.x, Django REST Framework, Gunicorn, Celery 5.x |
| **Databases & Caching** | PostgreSQL 16 (Alpine), Redis 7 (In-Memory LRU Cache & Broker) |
| **Storage & Documents** | ReportLab (Streaming PDF), Boto3, AWS S3 Glacier Instant Retrieval |

---

## 📁 Repository Structure

```text
money-management-system/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD: Lint, SAST, Trivy Scan, OIDC, SSM Rollout
├── terraform/                      # Modular Infrastructure as Code
│   ├── main.tf                     # S3 native locking backend, root providers, Budgets
│   ├── variables.tf                # Environment parameters and inputs
│   ├── outputs.tf                  # Instance IPs, S3 ARNs, SSM parameter paths
│   ├── terraform.tfvars.example    # Variable templates
│   └── modules/
│       ├── networking/             # VPC, Public Subnet, IGW, S3 Gateway Endpoint
│       ├── security/               # IAM OIDC Role, SSM Policies, Security Groups
│       ├── storage/                # Private S3 Bucket with 90-day Glacier Lifecycle
│       └── compute/                # EC2 t3.micro, 15GB EBS, 2GB Swap bootstrap script
├── backend/                        # Django REST API & Celery Worker
│   ├── Dockerfile                  # Multi-stage production build (non-root appuser)
│   ├── requirements.txt            # Production dependencies (gunicorn, boto3, celery)
│   ├── pytest.ini                  # PyTest configuration with coverage fail-under
│   ├── .coveragerc                 # Coverage omissions (migrations, manage.py)
│   ├── config/
│   │   ├── settings.py             # SSM-injected environment settings, Celery schedules
│   │   ├── celery.py               # Celery app initialization
│   │   └── urls.py                 # Core routing, Swagger UI & /api/health/ endpoint
│   ├── accounts/                   # Authentication & HttpOnly JWT cookie handling
│   └── transactions/               # Transaction CRUD, summary & S3 PDF tasks
├── frontend/                       # Modern Vanilla JS Single Page Application
│   ├── index.html                  # Main dashboard (balance, chart, transaction table)
│   ├── login.html                  # Login & registration portal
│   ├── css/                        # Responsive CSS3 styles
│   └── js/                         # API client & auth interceptor
├── nginx/
│   └── nginx.conf                  # Reverse proxy, rate limiting, and static serving
├── scripts/
│   └── deploy-ec2.sh               # EC2 rollout execution script (SSM Run Command target)
├── docker-compose.prod.yml         # Memory-tuned multi-container orchestration
└── README.md
```

---

## 🚦 CI/CD Pipeline Workflow

Every push to `main` triggers a 3-stage automated delivery pipeline:

```text
[ Push to main ]
       │
       ├──► 1. Quality & Linting Gate
       │       • Flake8 (PEP 8 linting)
       │       • Bandit (AST security scanning)
       │       • PyTest (30 unit tests, >80% coverage threshold)
       │
       ├──► 2. Build & Supply-Chain Security Gate
       │       • Assume AWS Role via OIDC (Short-lived token)
       │       • Multi-stage Docker build tagged with Git SHA
       │       • Trivy Container Scan (Fails on HIGH/CRITICAL vulnerabilities)
       │       • Push verified immutable tag to Amazon ECR
       │
       └──► 3. Zero-SSH Production Deployment
               • Package manifests & scripts into S3 deployment bundle
               • Dispatch AWS SSM Run Command to target instance (Tag: Project=MoneyManager)
               • Pull scanned container image from ECR
               • Decrypt runtime database & JWT secrets from SSM Parameter Store
               • Run zero-downtime database migrations & collectstatic
               • Execute rolling container recreate via Docker Compose
               • Restart Nginx to refresh Docker bridge upstream DNS
               • Poll 15-stage readiness probe at /api/health/ (HTTP 200 verification)
```

---

## ⚙️ Infrastructure Provisioning (Terraform)

### Prerequisites
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and configured with appropriate IAM permissions.
- [Terraform 1.10+](https://developer.hashicorp.com/terraform/install) installed.

### Quick Start
```bash
# 1. Clone the repository
git clone https://github.com/Sunil2409/money-management-system.git
cd money-management-system/terraform

# 2. Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values:
# alert_email, db_password, django_secret_key, jwt_secret_key

# 3. Initialize and apply infrastructure
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 4. View provisioned infrastructure outputs
terraform output ec2_public_ip
terraform output github_actions_role_arn
terraform output s3_bucket_name
```

---

## 💻 Local Development Setup

To run the full stack locally using Docker Compose:

```bash
# 1. Start all containers (Postgres, Redis, Django, Celery, Nginx)
docker compose up -d

# 2. Run initial database migrations
docker compose exec backend python manage.py migrate

# 3. Access local endpoints
# Frontend:     http://localhost/
# API Health:   http://localhost/api/health/
# Swagger UI:   http://localhost/api/docs/
# Django Admin: http://localhost/admin/
```

To run the test suite locally:
```bash
cd backend
pytest -v --cov=. --cov-report=term-missing --cov-fail-under=80
```

---

## 📊 Observability & Health Verification

The API exposes a comprehensive readiness endpoint at `/api/health/` that performs active connectivity checks against both database and caching tiers:

```bash
curl -i http://13.233.86.78/api/health/
```

**Response (`HTTP 200 OK`):**
```json
{
  "database": "healthy",
  "redis": "healthy"
}
```

If either the database connection drops or Redis fails to read back a test key, the endpoint immediately returns **`HTTP 503 Service Unavailable`**, preventing traffic routing during container restarts.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## 👤 Author

**Sunil Kumar E**  
DevOps / Cloud Infrastructure Engineer  
- GitHub: [@Sunil2409](https://github.com/Sunil2409)
- Repository: [money-management-system](https://github.com/Sunil2409/money-management-system)
