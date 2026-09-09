resource "aws_db_instance" "main" {
  identifier     = "${var.project}-${var.environment}"
  engine         = "postgres"
  engine_version = "17"

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage_gb
  max_allocated_storage = var.db_max_allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  multi_az               = var.db_multi_az
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.db_publicly_accessible

  backup_retention_period = var.db_backup_retention_days
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:30-mon:05:30"

  # A safety net, not a substitute for the real one-time bulk_uploader
  # dumpdata/loaddata described in aws_migration.md — this only protects
  # what's already landed in RDS, not what hasn't been migrated yet.
  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.project}-${var.environment}-final"
  deletion_protection       = true

  tags = { Name = "${var.project}-${var.environment}-db" }
}
