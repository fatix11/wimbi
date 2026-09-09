# Bridge-period debugging tool only - see enable_adminer's own note in
# variables.tf for the real HTTP-cleartext caveat before turning this on.
# Gated on enable_adminer (default false) so it can be switched off as
# cheaply as it was switched on.

resource "aws_security_group" "adminer" {
  count       = var.enable_adminer ? 1 : 0
  name_prefix = "${var.project}-${var.environment}-adminer-"
  vpc_id      = aws_vpc.main.id
  description = "Adminer web UI - reachable only from db_admin_cidrs, same list used for direct RDS access."

  dynamic "ingress" {
    for_each = length(var.db_admin_cidrs) > 0 ? [1] : []
    content {
      description = "Restricted to db_admin_cidrs"
      from_port   = 8080
      to_port     = 8080
      protocol    = "tcp"
      cidr_blocks = var.db_admin_cidrs
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-adminer-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_log_group" "adminer" {
  count             = var.enable_adminer ? 1 : 0
  name              = "/ecs/${var.project}-${var.environment}-adminer"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "adminer" {
  count                    = var.enable_adminer ? 1 : 0
  family                   = "${var.project}-${var.environment}-adminer"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "adminer"
      image     = "docker.io/library/adminer:4"
      essential = true

      portMappings = [{
        containerPort = 8080
        protocol      = "tcp"
      }]

      # Prefills the login form's server field - Adminer still asks for
      # username/password/database interactively, nothing is stored here.
      environment = [
        { name = "ADMINER_DEFAULT_SERVER", value = aws_db_instance.main.address },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.adminer[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "adminer"
        }
      }
    }
  ])

  tags = { Name = "${var.project}-${var.environment}-adminer-task" }
}

resource "aws_ecs_service" "adminer" {
  count           = var.enable_adminer ? 1 : 0
  name            = "${var.project}-${var.environment}-adminer"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.adminer[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.adminer[0].id]
    assign_public_ip = true # public subnet, no NAT Gateway - same reasoning as the app itself, see vpc.tf
  }
}
