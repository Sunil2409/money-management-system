resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "statements" {
  bucket        = "${var.bucket_name_prefix}-${random_id.bucket_suffix.hex}"
  force_destroy = true # Convenient for dev/testing; set to false in enterprise environments
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.statements.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sse" {
  bucket = aws_s3_bucket.statements.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public ingress (presigned URLs bypass this securely)
resource "aws_s3_bucket_public_access_block" "block_public" {
  bucket = aws_s3_bucket.statements.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# FinOps S3 Lifecycle Policy
resource "aws_s3_bucket_lifecycle_configuration" "lifecycle" {
  bucket = aws_s3_bucket.statements.id

  rule {
    id     = "archive-old-statements"
    status = "Enabled"

    filter {
      prefix = "statements/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}