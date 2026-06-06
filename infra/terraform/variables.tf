variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "project_name" {
  type    = string
  default = "job-crawler"
}

variable "image_uri" {
  description = "Full ECR image URI, e.g. 123456789012.dkr.ecr.eu-central-1.amazonaws.com/job-crawler:latest"
  type        = string
}

variable "lambda_timeout" {
  type    = number
  default = 300
}

variable "lambda_memory_size" {
  type    = number
  default = 256
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "schedule_timezone" {
  type    = string
  default = "Europe/Berlin"
}

# UTC RFC3339 cutoff after which schedules stop firing. Set just past the
# last desired run (19:00 Europe/Berlin on 2026-06-30 = 17:00 UTC).
variable "schedule_end_date" {
  type    = string
  default = "2026-07-01T00:00:00Z"
}

variable "schedule_xi_linkedin" {
  type    = string
  default = "cron(0 19 * * ? *)"
}

variable "schedule_hao_linkedin" {
  type    = string
  default = "cron(0 19 * * ? *)"
}

variable "schedule_hao_indeed" {
  type    = string
  default = "cron(0 19 * * ? *)"
}

variable "apify_api_key" {
  type      = string
  sensitive = true
}

variable "telegram_bot_token_xi" {
  type      = string
  sensitive = true
}

variable "telegram_chat_id_xi" {
  type      = string
  sensitive = true
}

variable "telegram_bot_token_hao" {
  type      = string
  sensitive = true
}

variable "telegram_chat_id_hao" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  default   = ""
  sensitive = true
}