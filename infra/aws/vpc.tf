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

# A publicly accessible RDS instance needs its ENI in a subnet whose route
# table actually reaches the internet gateway. A public IP alone is not
# enough: inbound still arrives (VPC-local routing), so the connection
# looks like it is being attempted, but the reply has no route back out and
# the client just times out. That failure is indistinguishable from a
# firewall block at the client end - both surface as SQLSTATE 08001 - which
# cost real debugging time here, so it is worth stating plainly.
#
# An earlier version made this group the union of public and private
# subnets, on the theory that AWS's ModifyDBSubnetGroup API refuses to
# remove a subnet an instance is actively using. That is true, but a union
# does not help: RDS simply kept its ENI in the private subnet it was
# already in. The working approach is a differently-named group holding
# only public subnets, so the instance is genuinely relocated rather than
# merely permitted to move. create_before_destroy sequences it: new group
# created, instance modified onto it, old group dropped once unused.
#
# Bridge-period only. Reverting db_publicly_accessible to false swaps this
# cleanly back to private-only - which is the intended end state once this
# lives in OAF's own AWS account and Airbyte reaches it over VPC peering.
resource "aws_db_subnet_group" "main" {
  name = var.db_publicly_accessible ? "${var.project}-${var.environment}-db-subnets-public" : "${var.project}-${var.environment}-db-subnets"

  subnet_ids = var.db_publicly_accessible ? aws_subnet.public[*].id : aws_subnet.private[*].id
  tags       = { Name = "${var.project}-${var.environment}-db-subnets" }

  lifecycle {
    create_before_destroy = true
  }
}
