# Real credentials live in Secrets Manager, not as plain environment
# variables on the task definition (which is visible to anyone with
# read access to the ECS console/API) — the task's execution role gets
# read-only access to exactly these two secrets, nothing else (iam.tf).

resource "aws_secretsmanager_secret" "django_secret_key" {
  name = "${var.project}-${var.environment}-django-secret-key"
}

resource "aws_secretsmanager_secret_version" "django_secret_key" {
  secret_id     = aws_secretsmanager_secret.django_secret_key.id
  secret_string = var.django_secret_key
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project}-${var.environment}-db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}
