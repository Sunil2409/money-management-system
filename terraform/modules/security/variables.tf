variable "vpc_id" { type = string }
variable "s3_bucket_arn" { type = string }
variable "environment" { type = string }
variable "db_password" { type = string; sensitive = true }
variable "django_secret_key" { type = string; sensitive = true }
variable "jwt_secret_key" { type = string; sensitive = true }