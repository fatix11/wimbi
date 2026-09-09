output "alb_dns_name" {
  description = "Visit this to reach the app once the ECS service is healthy. Also feed it into django_allowed_hosts on re-apply if you left that variable blank."
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "docker push target — see infra/aws/README.md for the build/push steps."
  value       = aws_ecr_repository.app.repository_url
}

output "rds_endpoint" {
  description = "Host:port for POSTGRES_HOST — also what OAF's Airbyte destination config needs once peering is in place."
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "Just the hostname, no port — what the ECS task definition actually uses for POSTGRES_HOST."
  value       = aws_db_instance.main.address
}

output "vpc_id" {
  description = "Needed on both sides when setting up VPC peering with OAF's Airbyte VPC."
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  value = aws_vpc.main.cidr_block
}

output "private_route_table_id" {
  description = "Where a route to OAF's peered VPC CIDR needs to be added once peering exists (see README)."
  value       = aws_route_table.private.id
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}
