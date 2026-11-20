output "instance_security_group_id" { value = aws_security_group.web_sg.id }
output "instance_profile_name" { value = aws_iam_instance_profile.profile.name }
output "ssm_prefix" { value = local.ssm_prefix }
output "github_actions_role_arn" { value = aws_iam_role.github_actions_oidc.arn }
