terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # S3 Native Conditional Write Locking (eliminates DynamoDB cost/need)
  # Uncomment after creating your state bucket:
  # backend "s3" {
  #   bucket       = "money-manager-tf-state-YOUR_ACCOUNT_ID"
  #   key          = "prod/terraform.tfstate"
  #   region       = "ap-south-1"
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "MoneyManager"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "networking" {
  source             = "./modules/networking"
  vpc_cidr           = "10.0.0.0/16"
  public_subnet_cidr = "10.0.1.0/24"
  availability_zone  = "${var.aws_region}a"
  environment        = var.environment
}

module "storage" {
  source             = "./modules/storage"
  bucket_name_prefix = "money-manager-statements-${var.environment}"
  environment        = var.environment
}

module "security" {
  source               = "./modules/security"
  vpc_id               = module.networking.vpc_id
  s3_bucket_arn        = module.storage.bucket_arn
  environment          = var.environment
  db_password          = var.db_password
  django_secret_key    = var.django_secret_key
  jwt_secret_key       = var.jwt_secret_key
}

module "compute" {
  source               = "./modules/compute"
  environment          = var.environment
  subnet_id            = module.networking.public_subnet_id
  security_group_id    = module.security.instance_security_group_id
  iam_instance_profile = module.security.instance_profile_name
  s3_bucket_name       = module.storage.bucket_name
  aws_region           = var.aws_region
  ebs_volume_size      = 15 # Stays safely below the 30 GB Free Tier ceiling
}

# AWS Free Tier Zero-Spend Safety Net Alert
resource "aws_budgets_budget" "zero_spend_guard" {
  name              = "money-manager-zero-spend-alert"
  budget_type       = "COST"
  limit_amount      = "1.00"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "ACTUAL"
    threshold                  = 80
    threshold_type              = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    notification_type          = "FORECASTED"
    threshold                  = 100
    threshold_type              = "PERCENTAGE"
    subscriber_email_addresses = [var.alert_email]
  }
}