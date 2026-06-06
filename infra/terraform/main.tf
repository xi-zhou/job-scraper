terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "job_crawler" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
}

# Expire old images once a new "latest" is pushed. Pushing a new image
# moves the "latest" tag forward, leaving the previous image untagged; this
# policy then deletes those untagged images (lifecycle eval is async, ~24h).
resource "aws_ecr_lifecycle_policy" "job_crawler" {
  repository = aws_ecr_repository.job_crawler.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images displaced by a newer latest"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role" "scheduler_exec" {
  name               = "${var.project_name}-scheduler-exec"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
}

data "aws_iam_policy_document" "scheduler_invoke_lambda" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.xi.arn, aws_lambda_function.hao.arn]
  }
}

resource "aws_iam_role_policy" "scheduler_invoke_lambda" {
  name   = "${var.project_name}-scheduler-invoke-lambda"
  role   = aws_iam_role.scheduler_exec.id
  policy = data.aws_iam_policy_document.scheduler_invoke_lambda.json
}

resource "aws_cloudwatch_log_group" "xi" {
  name              = "/aws/lambda/${var.project_name}-xi"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "hao" {
  name              = "/aws/lambda/${var.project_name}-hao"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "xi" {
  function_name = "${var.project_name}-xi"
  role          = aws_iam_role.lambda_exec.arn

  package_type = "Image"
  image_uri    = var.image_uri

  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  architectures = ["x86_64"]

  environment {
    variables = {
      APIFY_API_KEY      = var.apify_api_key
      TELEGRAM_BOT_TOKEN = var.telegram_bot_token_xi
      TELEGRAM_CHAT_ID   = var.telegram_chat_id_xi
      ANTHROPIC_API_KEY  = var.anthropic_api_key
      SCRAPER            = "linkedin"
      CONFIG_PATH        = "config-xi.yaml"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_logs,
    aws_cloudwatch_log_group.xi
  ]
}

resource "aws_lambda_function" "hao" {
  function_name = "${var.project_name}-hao"
  role          = aws_iam_role.lambda_exec.arn

  package_type = "Image"
  image_uri    = var.image_uri

  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  architectures = ["x86_64"]

  environment {
    variables = {
      APIFY_API_KEY      = var.apify_api_key
      TELEGRAM_BOT_TOKEN = var.telegram_bot_token_hao
      TELEGRAM_CHAT_ID   = var.telegram_chat_id_hao
      ANTHROPIC_API_KEY  = var.anthropic_api_key
      SCRAPER            = "linkedin"
      CONFIG_PATH        = "config-hao.yaml"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_logs,
    aws_cloudwatch_log_group.hao
  ]
}

resource "aws_scheduler_schedule" "xi_linkedin" {
  name                         = "${var.project_name}-xi-linkedin"
  schedule_expression          = var.schedule_xi_linkedin
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.xi.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    input = jsonencode({
      scraper     = "linkedin"
      config_path = "config-xi.yaml"
    })
  }
}

resource "aws_scheduler_schedule" "hao_linkedin" {
  name                         = "${var.project_name}-hao-linkedin"
  schedule_expression          = var.schedule_hao_linkedin
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.hao.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    input = jsonencode({
      scraper     = "linkedin"
      config_path = "config-hao.yaml"
    })
  }
}

resource "aws_scheduler_schedule" "hao_indeed" {
  name                         = "${var.project_name}-hao-indeed"
  schedule_expression          = var.schedule_hao_indeed
  schedule_expression_timezone = var.schedule_timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.hao.arn
    role_arn = aws_iam_role.scheduler_exec.arn

    input = jsonencode({
      scraper     = "indeed"
      config_path = "config-hao.yaml"
    })
  }
}