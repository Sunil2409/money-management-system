💳 Cloud-Native Money Manager & FinOps Platform
A production-engineered, cost-optimized financial ledger designed for zero-downtime deployment on the AWS Free Tier ($0.00/month).
Engineered with Terraform (IaC), keyless AWS OIDC GitHub Actions CI/CD, automated Trivy/Bandit DevSecOps barriers, asynchronous Celery worker pipelines, and AWS Systems Manager (SSM) zero-SSH orchestration.
🏛️ System Architecture
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
    │  [ AWS Systems Manager ] ──────► Dispatches Run Command             │
    │                                         │                           │
    │  ┌── VPC (10.0.0.0/16) ─────────────────┼────────────────────────┐  │
    │  │                                      ▼                        │  │
    │  │  ┌── EC2 t3.micro Host (1GB RAM + 2GB Swapfile on EBS) ────┐  │  │
    │  │  │                                                         │  │  │
    │  │  │  [ Nginx:alpine ] (Ports 80/443, TLS, Rate Limiting)   │  │  │
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
    │  └───────────────────────────────────────────────────────────────┘  │
    │                                                                     │
    │  [ AWS Budgets ] ──► Hard Alert at $1.00 USD Spend Threshold        │
    └─────────────────────────────────────────────────────────────────────┘
🚀 Key DevOps & Engineering Highlights
1. Zero-SSH GitOps Continuous Deployment
AWS Systems Manager (SSM) Run Command: Deployments contain zero long-lived SSH daemon keys. GitHub Actions targets running instances by AWS resource tags (Project=MoneyManager) using dynamic document execution.
Automated Rollback & Readiness Probes: The deployment script polls an internal health check (/api/health/) verifying PostgreSQL connection and Redis readback across 12 automated intervals before terminating old container processes.
2. Supply Chain Security & DevSecOps
Keyless AWS Authentication (OIDC): Eliminates hardcoded AWS_ACCESS_KEY_ID secrets from GitHub. Runners authenticate directly through AWS Security Token Service (STS) using short-lived tokens restricted to repository sub-claims.
Pipeline Security Gates:
Static Application Security Testing (SAST): Automated bandit scanning blocks dangerous function execution or insecure bindings.
Container Vulnerability Auditing: Integrated trivy container scanning automatically breaks the build upon detecting unpatched HIGH or CRITICAL CVEs.
Quality Enforcement: Automated pytest suite enforcing an 80%+ branch coverage gate before container compilation.
3. FinOps & Low-Memory Linux Engineering
True $0.00/Month AWS Free Tier Compliance:
Compute: Single t3.micro instance (750 hours/month Free Tier allocation).
Storage: 15 GB encrypted gp3 root EBS (safely within the 30 GB account cap).
Networking: Leverages an S3 Gateway VPC Endpoint (free) avoiding costly NAT Gateways ($32+/month).
Budget Safety: An aws_budgets_budget sends immediate email alerts upon actual or forecasted spend exceeding $1.00 USD.
2 GB Linux EBS Swap Buffer: Deployed via Terraform user_data bootstrap scripts with vm.swappiness=10, expanding total addressable memory to 3 GB and preventing Linux Out-Of-Memory (OOM) killer terminations.
Container Memory Boundaries: Hard Docker memory limits (mem_limit) and task throttling maintain maximum concurrent RAM consumption under 620 MB:
Nginx (32M), PostgreSQL (140M), Redis (64M), Django (220M), Celery (160M).
4. Asynchronous Event-Driven Architecture
Combined Celery Worker & Beat Engine: Executes both scheduled periodic cron tasks and asynchronous job queues in a single low-memory Python process (--beat --concurrency=1).
Non-Blocking PDF Generation Pipeline:
Monthly account statements are compiled in memory using ReportLab without generating intermediate disk artifacts.
Uploads stream directly to a private, encrypted S3 bucket using boto3.
Multi-tenant authorization generates time-limited (15-minute) Presigned S3 URLs—preventing public S3 bucket exposure.
Lifecycle Data Tiering: S3 objects automatically transition to Glacier Instant Retrieval after 90 days and expire after 365 days using automated S3 Lifecycle rules.
🛠️ Technology Stack
Layer	Tools & Technologies
Infrastructure as Code	Terraform 1.10+ (Modular, Native S3 Conditional Write State Locking)
Cloud Provider	AWS (EC2, S3, ECR, VPC, IAM, SSM, CloudWatch, Budgets)
CI/CD & Security	GitHub Actions, AWS OIDC, Trivy, Bandit, Flake8, PyTest-Cov
Containers & Runtime	Docker, Docker Compose V2, Alpine Linux, Nginx 1.25
Backend & Workers	Python 3.12, Django 5.x, Django REST Framework, Celery 5.x
Databases & Queues	PostgreSQL 16 (Alpine), Redis 7 (In-Memory LRU Cache & Broker)
Storage & Document Gen	ReportLab (Streaming PDF), Boto3, AWS S3 Glacier Instant Retrieval
📁 Repository Structure
money-management-system/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD: Lint, SAST, Trivy Scan, OIDC, SSM Rollout
├── terraform/                      # Modular Infrastructure as Code
│   ├── main.tf                     # S3 native locking backend, root providers, Budgets
│   ├── variables.tf                # Environment parameters and inputs
│   ├── outputs.tf                  # Instance IPs, S3 ARNs, SSM parameter paths
│   └── modules/
│       ├── networking/             # VPC, Public Subnet, IGW, S3 Gateway Endpoint
│       ├── security/               # IAM OIDC Role, SSM Policies, Security Groups
│       ├── storage/                # Private S3 Bucket with 90-day Glacier Lifecycle
│       └── compute/                # EC2 t3.micro, 15GB EBS, 2GB Swap bootstrap script
├── backend/                        # Django REST API & Celery Worker
│   ├── Dockerfile                  # Multi-stage production build (non-root user)
│   ├── requirements.txt            # Production dependencies (gunicorn, boto3, celery)
│   ├── config/
│   │   ├── settings.py             # SSM-injected environment settings, Celery schedules
│   │   ├── celery.py               # Celery app initialization
│   │   └── urls.py                 # Core routing & /api/health/ endpoint
│   ├── accounts/                   # Authentication & token handling
│   └── transactions/
│       ├── tasks.py                # Asynchronous ReportLab PDF statement generation
│       └── views.py                # Transaction CRUD & Presigned S3 download API
├── nginx/
│   └── nginx.conf                  # Reverse proxy, rate limiting, and static proxying
├── docker-compose.prod.yml         # Memory-tuned multi-container orchestration
└── README.md
🚦 CI/CD & Automated Pipeline Architecture
[ Push to main ]
       │
       ├──► 1. Quality & Linting Gate
       │       • Flake8 (PEP8 formatting verification)
       │       • Bandit (AST security scanning)
       │       • PyTest (Fails if line coverage < 80%)
       │
       ├──► 2. Build & Supply-Chain Scan
       │       • Assume AWS Role via OIDC (Short-lived token)
       │       • Multi-stage Docker build tagged with Git SHA
       │       • Trivy Container Scan (Fails on HIGH/CRITICAL vulnerabilities)
       │       • Push verified immutable tag to Amazon ECR
       │
       └──► 3. Zero-SSH Production Deployment
               • Dispatch AWS SSM Run Command to EC2
               • Decrypt runtime parameters from AWS SSM Parameter Store
               • Pull latest ECR image tag
               • Execute rolling container recreate via Docker Compose
               • Verify 12-stage readiness probe at /api/health/
               • Auto-abort and emit diagnostic logs on failure
⚙️ Infrastructure Provisioning (Terraform)
Prerequisites
AWS CLI installed and configured
Terraform 1.10+ installed
Deployment Steps
Clone the repository:
Bash
git clone https://github.com/Sunil2409/money-management-system.git
cd money-management-system/terraform
Configure your variables:
Bash
cp terraform.tfvars.example terraform.tfvars
# Fill in alert_email, db_password, django_secret_key, and jwt_secret_key
Initialize and provision infrastructure:
Bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
Retrieve infrastructure outputs:
Bash
terraform output ec2_public_ip
terraform output github_actions_role_arn
📊 Observability & Health Verification
The API exposes a readiness probe at /api/health/ that runs active connectivity checks against both database and caching tiers:
Bash
# Verify system readiness
curl -i http://<YOUR_EC2_PUBLIC_IP>/api/health/
Response (HTTP 200 OK):
JSON
{
  "database": "healthy",
  "redis": "healthy"
}
If either the database connection drops or Redis fails to read back a test key, the endpoint immediately returns HTTP 503 Service Unavailable, preventing traffic routing during container restarts.
📄 License
Distributed under the MIT License. See LICENSE for more information.
👤 Author
Sunil Kumar E
DevOps / Cloud Infrastructure Engineer
GitHub: @Sunil2409