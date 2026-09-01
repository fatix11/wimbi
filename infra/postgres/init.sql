-- Runs once, on first container init (docker-entrypoint-initdb.d).
-- analytics_mirror: landed by Airbyte from Snowflake ANALYTICS.REPORTING /
-- MASTER.BRIDGE_CLIENT_SOURCE_IDS (see _docs/architectural_decisions.md ADR-003).
-- Django's own tables live in the default "public" schema.
CREATE SCHEMA IF NOT EXISTS analytics_mirror;
GRANT ALL ON SCHEMA analytics_mirror TO wimbi;
