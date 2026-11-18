variable "aws_region" {
  type        = string
  default     = "ap-south-1"
  description = "Target AWS Region"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Environment identifier"
}

variable "alert_email" {
  type        = string
  description = "Email address for AWS Budget cost spike notifications"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL root password for SSM Parameter Store"
}

variable "django_secret_key" {
  type        = string
  sensitive   = true
  description = "Django secret key for production"
}

variable "jwt_secret_key" {
  type        = string
  sensitive   = true
  description = "JWT authentication secret key"
}