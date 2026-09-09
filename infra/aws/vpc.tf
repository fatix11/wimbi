# Public subnets hold the ALB *and* the ECS tasks — deliberately, not the
# more textbook "tasks in private subnets behind a NAT Gateway" pattern.
# A NAT Gateway alone runs ~$32/month for a single-instance app that has no
# real need for one (the task doesn't need to *initiate* outbound
# connections beyond pulling its own image and reaching AWS APIs, both
# reachable from a public subnet directly). Security comes from the task's
# own security group (ecs_tasks, in security_groups.tf) allowing inbound
# only from the ALB's security group — not from subnet placement. RDS stays
# in the private subnets below with no public IP at all, full stop.

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.project}-${var.environment}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-${var.environment}-igw" }
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project}-${var.environment}-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + 8)
  availability_zone = var.availability_zones[count.index]

  tags = { Name = "${var.project}-${var.environment}-private-${count.index}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project}-${var.environment}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# No route out to the internet from here on purpose — RDS never needs one,
# and it's the one thing in this stack that must never be reachable from
# the public internet. The only route added here will be the VPC peering
# route to OAF's Airbyte VPC, once that connection exists (see README).
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-${var.environment}-private-rt" }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_db_subnet_group" "main" {
  name = "${var.project}-${var.environment}-db-subnets"
  # Adds the public subnets rather than swapping to them - AWS's
  # ModifyDBSubnetGroup API refuses to remove a subnet the instance's ENI
  # is actively using ("Some of the subnets to be deleted are currently in
  # use"), so a straight swap fails on an already-running instance. Union
  # of both avoids ever removing a subnet mid-use; the instance itself
  # (publicly_accessible in rds.tf) decides whether it actually gets a
  # public IP, this group just makes both kinds of subnet available to it.
  # Bridge-period setting for OAF's external Airbyte to reach this without
  # VPC peering - revert once this migrates into OAF's own AWS account.
  subnet_ids = var.db_publicly_accessible ? concat(aws_subnet.public[*].id, aws_subnet.private[*].id) : aws_subnet.private[*].id
  tags       = { Name = "${var.project}-${var.environment}-db-subnets" }
}
