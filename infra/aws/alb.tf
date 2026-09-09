resource "aws_lb" "main" {
  name               = "${var.project}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = { Name = "${var.project}-${var.environment}-alb" }
}

resource "aws_lb_target_group" "app" {
  name        = "${var.project}-${var.environment}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # Fargate tasks are addressed by ENI IP, not instance id

  health_check {
    path                = "/login/"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.project}-${var.environment}-tg" }
}

# HTTP only to start — add an aws_lb_listener on 443 with an ACM cert once
# a real domain is pointed at this ALB (see README), and change this
# listener's default_action to redirect to https instead of forwarding.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
