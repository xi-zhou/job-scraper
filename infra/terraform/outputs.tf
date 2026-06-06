output "lambda_function_xi_name" {
  value = aws_lambda_function.xi.function_name
}

output "lambda_function_hao_name" {
  value = aws_lambda_function.hao.function_name
}

output "xi_rule_name" {
  value = aws_scheduler_schedule.xi_linkedin.name
}

output "hao_linkedin_rule_name" {
  value = aws_scheduler_schedule.hao_linkedin.name
}

output "hao_indeed_rule_name" {
  value = aws_scheduler_schedule.hao_indeed.name
}

