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

# No route out to the internet from here by default — RDS never needs one,
# and it's the one thing in this stack that must never be reachable from
# the public internet. The only route added here will be the VPC peering
# route to OAF's Airbyte VPC, once that connection exists (see README).
# The one exception is the bridge-period IGW route below.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-${var.environment}-private-rt" }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# READ THIS BEFORE PUTTING ANYTHING NEW IN A "PRIVATE" SUBNET.
#
# While db_publicly_accessible is true, the private subnets are not private:
# this route gives them a path to the internet gateway, so anything placed
# there can reach the internet and, with a public IP plus a permissive
# security group, be reached from it. Today RDS is the only occupant, its
# inbound is restricted to the app's own tasks plus airbyte_source_cidrs,
# and it already carries a public IP by explicit choice - so the practical
# exposure added here is close to nil. The hazard is future work trusting
# the subnet name instead of this file.
#
# Why the route rather than moving RDS into the real public subnets, which
# would be the cleaner shape: RDS will not do it. ModifyDBInstance's
# DBSubnetGroupName parameter exists to move an instance to a *different
# VPC*, and rejects a same-VPC subnet group with
# "InvalidVPCNetworkStateFault: ... Choose a DB subnet group in different
# VPC". Confirmed the hard way on 2026-09-09 - two Terraform applies and
# the console's own modify flow all failed identically. A snapshot-restore
# onto a new instance would work but changes the endpoint hostname and
# rebuilds the database, which is not worth it for a few weeks of bridge.
#
# A publicly accessible instance needs its subnet's route table to reach an
# IGW; without it the inbound SYN arrives fine over VPC-local routing (so
# flow logs can even show it being allowed or rejected) but the reply has
# no way back out, and the client sees a plain timeout. That surfaces as
# SQLSTATE 08001 - identical to a firewall block, which is exactly what
# sent this debugging session down the wrong path for a while.
#
# Ends with the bridge: setting db_publicly_accessible = false removes this
# route and the private subnets become genuinely private again.
resource "aws_route" "private_igw_bridge" {
  count                  = var.db_publicly_accessible ? 1 : 0
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Private subnets only, unconditionally - reachability for OAF's Airbyte is
# handled by aws_route.private_igw_bridge above, not by subnet placement.
#
# Two earlier attempts to vary this by db_publicly_accessible are worth not
# repeating. Making it the union of public and private did nothing: RDS
# keeps its ENI wherever it already is and simply ignores newly available
# subnets. Swapping it to public-only cannot work either, because RDS
# refuses same-VPC subnet group changes outright (see the route above).
# Since the instance can never actually move, the group's membership has no
# bearing on connectivity, and the honest thing is to leave it describing
# where RDS genuinely lives.
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${var.project}-${var.environment}-db-subnets" }
}
