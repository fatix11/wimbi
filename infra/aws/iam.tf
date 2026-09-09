data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Execution role — what ECS itself needs to start the task: pull the image,
# write logs, read the two secrets above. Not the app's own permissions.
resource "aws_iam_role" "ecs_execution" {
  name               = "${var.project}-${var.environment}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_execution_secrets" {
  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.django_secret_key.arn,
      aws_secretsmanager_secret.db_password.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name   = "${var.project}-${var.environment}-secrets-read"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution_secrets.json
}

# Task role — what the *app itself* can do via AWS APIs at runtime. Empty
# for now: the app doesn't call any AWS service directly today (no S3, no
# SES, nothing). Kept as its own role rather than reusing the execution
# role, so adding a real permission later doesn't also widen what ECS
# itself can do.
resource "aws_iam_role" "ecs_task" {
  name               = "${var.project}-${var.environment}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json
}
