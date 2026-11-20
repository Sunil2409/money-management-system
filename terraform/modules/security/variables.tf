variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "s3_bucket_arn" {
  type        = string
  description = "S3 bucket ARN"
}

variable "environment" {
  type        = string
  description = "Environment identifier"
}

variable "aws_region" {
  type        = string
  description = "Target AWS Region"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL root password"
}

variable "django_secret_key" {
  type        = string
  sensitive   = true
  description = "Django secret key"
}

variable "jwt_secret_key" {
  type        = string
  sensitive   = true
  description = "JWT authentication secret key"
}
