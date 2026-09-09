resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project}-${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project}-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.container_image
      essential = true

      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]

      environment = [
        { name = "DJANGO_DEBUG", value = "False" },
        { name = "DJANGO_ALLOWED_HOSTS", value = var.django_allowed_hosts != "" ? var.django_allowed_hosts : aws_lb.main.dns_name },
        { name = "POSTGRES_DB", value = var.db_name },
        { name = "POSTGRES_USER", value = var.db_username },
        { name = "POSTGRES_HOST", value = aws_db_instance.main.address },
        { name = "POSTGRES_PORT", value = "5432" },
      ]

      secrets = [
        { name = "DJANGO_SECRET_KEY", valueFrom = aws_secretsmanager_secret.django_secret_key.arn },
        { name = "POSTGRES_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "app"
        }
      }
    }
  ])

  tags = { Name = "${var.project}-${var.environment}-task" }
}

resource "aws_ecs_service" "app" {
  name            = "${var.project}-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true # public subnet, no NAT Gateway — see vpc.tf's note
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition] # let CI/CD (once it exists) redeploy new image tags without terraform reverting them
  }
}
