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

output "github_actions_role_arn" {
  description = "Role ARN to set in GitHub repository secret AWS_ROLE_TO_ASSUME"
  value       = module.security.github_actions_role_arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.app.repository_url
}
