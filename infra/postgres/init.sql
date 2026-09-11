-- Runs once, on first container init (docker-entrypoint-initdb.d).
-- analytics_mirror: landed by Airbyte from Snowflake ANALYTICS.REPORTING /
-- MASTER.BRIDGE_CLIENT_SOURCE_IDS (see _docs/architectural_decisions.md ADR-003).
-- Django's own tables live in the default "public" schema.
CREATE SCHEMA IF NOT EXISTS analytics_mirror;
GRANT ALL ON SCHEMA analytics_mirror TO wimbi;

-- analytics_mirror_raw: mirrors the AWS shape (see infra/postgres/analytics_mirror_views.sql
-- and _docs/local_vs_cloud.md) - Airbyte's own landing schema on AWS, empty here on
-- purpose. Nothing auto-populates it locally; load a real or trimmed snapshot into it
-- yourself, matching Snowflake's uppercase column names, then point an
-- analytics_mirror view at it the same way the AWS script does.
CREATE SCHEMA IF NOT EXISTS analytics_mirror_raw;
GRANT ALL ON SCHEMA analytics_mirror_raw TO wimbi;
