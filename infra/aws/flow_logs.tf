# Temporary, for discovering OAF's Airbyte outbound IP without needing
# DevOps/infra team access - REJECT-only keeps volume low (we only care
# about blocked connection attempts, not all normal app/ALB traffic).
# Short retention since this is a one-time discovery tool, not ongoing
# monitoring. Safe to remove once airbyte_source_cidrs is set and confirmed
# working, though cheap enough to just leave running too.

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/vpc/${var.project}-${var.environment}-flow-logs"
  retention_in_days = 7
}

data "aws_iam_policy_document" "vpc_flow_logs_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "vpc_flow_logs" {
  name               = "${var.project}-${var.environment}-vpc-flow-logs"
  assume_role_policy = data.aws_iam_policy_document.vpc_flow_logs_assume_role.json
}

data "aws_iam_policy_document" "vpc_flow_logs_publish" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "vpc_flow_logs_publish" {
  name   = "${var.project}-${var.environment}-vpc-flow-logs-publish"
  role   = aws_iam_role.vpc_flow_logs.id
  policy = data.aws_iam_policy_document.vpc_flow_logs_publish.json
}

resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "REJECT"
  vpc_id          = aws_vpc.main.id

  # 60s instead of the 600s default. While this is being used to chase a
  # specific connection attempt, a 10-minute aggregation window makes
  # "nothing logged yet" and "nothing was rejected" indistinguishable -
  # which is the one distinction the log is here to make. Costs slightly
  # more log volume; irrelevant at REJECT-only volumes.
  max_aggregation_interval = 60
}
