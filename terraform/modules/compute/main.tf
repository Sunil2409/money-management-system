data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app_server" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = "t3.micro" # AWS Free Tier eligible (750 hours/month)
  subnet_id            = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  iam_instance_profile = var.iam_instance_profile

  root_block_device {
    volume_size           = var.ebs_volume_size # 15 GB (stays under 30 GB total EBS quota)
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    aws_region     = var.aws_region
    s3_bucket_name = var.s3_bucket_name
    environment    = var.environment
  })

  tags = {
    Name    = "money-manager-${var.environment}-instance"
    Project = "MoneyManager"
  }

  lifecycle {
    ignore_changes = [ami]
  }
}