resource "aws_security_group" "alb" {
  name_prefix = "${var.project}-${var.environment}-alb-"
  vpc_id      = aws_vpc.main.id
  description = "Public-facing ALB — the only thing in this stack open to the internet."

  ingress {
    description = "HTTP from anywhere (add a 443 rule once a TLS cert exists — see README)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-alb-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project}-${var.environment}-ecs-"
  vpc_id      = aws_vpc.main.id
  description = "The app itself — even though it sits in a public subnet, only the ALB can reach it, nothing else."

  ingress {
    description     = "Only from the ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-ecs-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project}-${var.environment}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Postgres — reachable only from the app's own tasks, plus OAF's Airbyte once peered. Never public."

  ingress {
    description     = "The app itself"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  dynamic "ingress" {
    for_each = var.airbyte_source_cidr != null ? [var.airbyte_source_cidr] : []
    content {
      description = "OAF's self-hosted Airbyte — requires the actual network path (VPC peering/VPN) to exist too, this rule alone isn't sufficient. See README."
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-rds-sg" }

  lifecycle {
    create_before_destroy = true
  }
}
