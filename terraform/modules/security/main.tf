# Security Group
resource "aws_security_group" "web_sg" {
  name        = "money-manager-${var.environment}-web-sg"
  description = "Allow HTTP, HTTPS, and SSH ingress only"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP ingress for Certbot and web traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS ingress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH fallback (restrict to your IP in production)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

# IAM Role for EC2 Instance Profile (Zero static keys on server)
resource "aws_iam_role" "ec2_role" {
  name = "money-manager-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# S3 Access Policy (Least Privilege)
resource "aws_iam_policy" "s3_access" {
  name = "money-manager-${var.environment}-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

# SSM Parameter Store Access Policy
resource "aws_iam_policy" "ssm_read" {
  name = "money-manager-${var.environment}-ssm-read-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/moneymanager/${var.environment}/*"
      }
    ]
  })
}

# Attach AWS Managed SSM Agent Policy (Enables AWS Session Manager & Run Command)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_role_policy_attachment" "ssm_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ssm_read.arn
}

resource "aws_iam_instance_profile" "profile" {
  name = "money-manager-${var.environment}-instance-profile"
  role = aws_iam_role.ec2_role.name
}

# SSM Standard Parameters (100% Free Forever)
locals {
  ssm_prefix = "/moneymanager/${var.environment}"
}

resource "aws_ssm_parameter" "db_password" {
  name        = "${local.ssm_prefix}/POSTGRES_PASSWORD"
  description = "Database master password"
  type        = "SecureString"
  value       = var.db_password
  tier        = "Standard"
}

resource "aws_ssm_parameter" "django_secret" {
  name        = "${local.ssm_prefix}/SECRET_KEY"
  description = "Django application secret key"
  type        = "SecureString"
  value       = var.django_secret_key
  tier        = "Standard"
}

resource "aws_ssm_parameter" "jwt_secret" {
  name        = "${local.ssm_prefix}/JWT_SECRET_KEY"
  description = "JWT authentication secret key"
  type        = "SecureString"
  value       = var.jwt_secret_key
  tier        = "Standard"
}

# 1. GitHub OIDC Identity Provider (Create only once per AWS account)
data "aws_partition" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
    "d367a47959a77b088bec4fe3e7dd3ec9ba733ab5"
  ]
}

# 2. IAM Role Assumed by GitHub Actions via OIDC
resource "aws_iam_role" "github_actions_oidc" {
  name = "money-manager-${var.environment}-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            "repo:Sunil2409/money-management-system:*",
            "repo:sunil2409/money-management-system:*",
            "*money-management-system*"
          ]
        }
      }
    }]
  })
}

# 3. Least-Privilege Policy: ECR Push + SSM Run Command on Target Instance
resource "aws_iam_policy" "github_actions_deploy" {
  name = "money-manager-${var.environment}-ci-cd-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR Authentication & Push Permissions
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:CompleteLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:InitiateLayerUpload",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:BatchGetImage"
        ]
        Resource = "arn:aws:ecr:${var.aws_region}:*:repository/money-manager"
      },
      # SSM Run Command Permissions targeting specific project instances
      {
        Effect   = "Allow"
        Action   = ["ssm:SendCommand"]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:*:document/AWS-RunShellScript",
          "arn:aws:ec2:${var.aws_region}:*:instance/*"
        ]
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Project" = "MoneyManager"
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:ListCommands"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "github_oidc_attach" {
  role       = aws_iam_role.github_actions_oidc.name
  policy_arn = aws_iam_policy.github_actions_deploy.arn
}