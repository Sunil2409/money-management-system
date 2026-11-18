variable "environment" { type = string }
variable "subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "iam_instance_profile" { type = string }
variable "s3_bucket_name" { type = string }
variable "aws_region" { type = string }
variable "ebs_volume_size" { 
  type    = number 
  default = 15 
}