output "ec2_public_ip" {
  description = "Public IP address of the deployed EC2 instance"
  value       = module.compute.public_ip
}

output "s3_bucket_name" {
  description = "S3 bucket name used for PDF statement storage"
  value       = module.storage.bucket_name
}

output "ssm_parameter_path" {
  description = "SSM Parameter Store root hierarchy"
  value       = module.security.ssm_prefix
}