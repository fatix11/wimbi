-- Local counterpart to infra/postgres/analytics_mirror_views.sql (the AWS
-- version). Same idea - analytics_mirror_raw is the landing zone,
-- analytics_mirror holds views translating it to what Django expects -
-- but NOT the same SQL verbatim: DBeaver landed local raw tables
-- unquoted/lowercase (analytics_mirror_raw.dim_client, not
-- analytics_mirror_raw."DIM_CLIENT" the way Airbyte does on AWS), even
-- though the column names inside came through quoted-uppercase, same as
-- AWS. Table-name casing differs by source tool; column casing doesn't.
--
-- Scope of this pass, deliberately narrow: only tables where no existing
-- real local data was at risk - see _docs/local_vs_cloud.md and this
-- session's own alignment check for the full inventory. fo_performance's
-- existing table was empty (0 rows) so converting it to a view was safe;
-- the six DIM_* tables are brand new Django models with nothing to lose.
-- Explicitly NOT touched here: dim_country, dim_mcf, dim_program,
-- dim_season, dim_system, bridge_client_source_ids, program_summary -
-- all already have real local data as physical tables; converting those
-- needs an explicit decision, not a side effect of this pass.
--
-- These do NOT get added to analytics_mirror/seed_data.py's MIRROR_MODELS
-- tuple - that list is for ensure_analytics_tables to create EMPTY TABLES
-- for Airbyte to land into directly, which is exactly the pattern these
-- six are superseding. Adding them there would fight this file.

DROP TABLE IF EXISTS analytics_mirror.fo_performance;
CREATE VIEW analytics_mirror.fo_performance AS
SELECT
  "FO_KEY"                       AS fo_key,
  "FO_NAME"                      AS fo_name,
  "COUNTRY"                      AS country,
  "FO_ID"                        AS fo_id,
  "UNIQUE_CLIENTS"               AS unique_clients,
  "LOAN_CLIENTS"                 AS loan_clients,
  "TOTAL_LOANS"                  AS total_loans,
  "TOTAL_PRINCIPAL_LCY"          AS total_principal_lcy,
  "TOTAL_REPAID_LCY"             AS total_repaid_lcy,
  "TOTAL_OUTSTANDING_LCY"        AS total_outstanding_lcy,
  "PORTFOLIO_REPAYMENT_RATE_PCT" AS portfolio_repayment_rate_pct,
  "AT_RISK_LOANS"                AS at_risk_loans,
  "AT_RISK_OUTSTANDING_LCY"      AS at_risk_outstanding_lcy,
  "SALE_CLIENTS"                 AS sale_clients,
  "TOTAL_ORDERS"                 AS total_orders,
  "TOTAL_SALES_LCY"              AS total_sales_lcy,
  "PROGRAMS_COVERED"             AS programs_covered
FROM analytics_mirror_raw.v_fo_performance;

DROP TABLE IF EXISTS analytics_mirror.dim_client;
CREATE VIEW analytics_mirror.dim_client AS
SELECT
  "GL_CLIENT_ID"           AS gl_client_id,
  "CLUSTER_SEQ"            AS cluster_seq,
  "FIRST_NAME"             AS first_name,
  "LAST_NAME"              AS last_name,
  "FULL_NAME"              AS full_name,
  "PHONE"                  AS phone,
  "NATIONAL_ID"            AS national_id,
  "ACCOUNT_NUMBER"         AS account_number,
  "FINERACT_ID"            AS fineract_id,
  "GENDER"                 AS gender,
  "DATE_OF_BIRTH"          AS date_of_birth,
  "COUNTRY"                AS country,
  "COUNTRY_CODE"           AS country_code,
  "PRIMARY_SOURCE_SYSTEM"  AS primary_source_system,
  "PRIMARY_PROGRAM"        AS primary_program,
  "PRIMARY_SITE"           AS primary_site,
  "SOURCE_RECORD_COUNT"    AS source_record_count,
  "IS_SINGLETON"           AS is_singleton,
  "IS_REVIEWED"            AS is_reviewed,
  "IS_ACTIVE"              AS is_active,
  "CREATED_TS"             AS created_ts,
  "LAST_UPDATED_TS"        AS last_updated_ts
FROM analytics_mirror_raw.dim_client;

DROP TABLE IF EXISTS analytics_mirror.dim_date;
CREATE VIEW analytics_mirror.dim_date AS
SELECT
  "DATE_KEY"       AS date_key,
  "DATE"           AS date,
  "YEAR"           AS year,
  "QUARTER"        AS quarter,
  "QUARTER_NAME"   AS quarter_name,
  "MONTH"          AS month,
  "MONTH_SHORT"    AS month_short,
  "MONTH_NAME"     AS month_name,
  "YEAR_MONTH_KEY" AS year_month_key,
  "YEAR_MONTH"     AS year_month,
  "WEEK_OF_YEAR"   AS week_of_year,
  "DAY_OF_YEAR"    AS day_of_year,
  "DAY_OF_MONTH"   AS day_of_month,
  "DAY_OF_WEEK"    AS day_of_week,
  "DAY_SHORT"      AS day_short,
  "DAY_NAME"       AS day_name,
  "IS_WEEKEND"     AS is_weekend,
  "IS_WEEKDAY"     AS is_weekday
FROM analytics_mirror_raw.dim_date;

DROP TABLE IF EXISTS analytics_mirror.dim_exchange_rate;
CREATE VIEW analytics_mirror.dim_exchange_rate AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "COUNTRY_CODE", "YEAR_MONTH", "TARGET_CURRENCY") AS id,
  "COUNTRY_ID"       AS country_id,
  "COUNTRY_CODE"     AS country_code,
  "YEAR_MONTH"       AS year_month,
  "TARGET_CURRENCY"  AS target_currency,
  "RATE_EXACT"       AS rate_exact,
  "USD_RATE"         AS usd_rate,
  "IS_EXACT_MATCH"   AS is_exact_match
FROM analytics_mirror_raw.dim_exchange_rate;

DROP TABLE IF EXISTS analytics_mirror.dim_location;
CREATE VIEW analytics_mirror.dim_location AS
SELECT
  "LOCATION_KEY" AS location_key,
  "COUNTRY"      AS country,
  "REGION"       AS region,
  "DISTRICT"     AS district,
  "SECTOR"       AS sector,
  "LOWEST_LOC"   AS lowest_loc,
  "LOC_TYPE"     AS loc_type,
  "LATITUDE"     AS latitude,
  "LONGITUDE"    AS longitude,
  "GEOPOINT"     AS geopoint,
  "LOC_PARENTS"  AS loc_parents
FROM analytics_mirror_raw.dim_location;

DROP TABLE IF EXISTS analytics_mirror.dim_people;
CREATE VIEW analytics_mirror.dim_people AS
SELECT
  "PEOPLE_KEY"         AS people_key,
  "FULL_NAME"          AS full_name,
  "FIRST_NAME"         AS first_name,
  "LAST_NAME"          AS last_name,
  "IS_FO"              AS is_fo,
  "IS_SHOPKEEPER"      AS is_shopkeeper,
  "IS_NURSERY_MANAGER" AS is_nursery_manager,
  "DIVISION"           AS division,
  "SOURCE_SYSTEM"      AS source_system,
  "COUNTRY"            AS country,
  "EMAIL"              AS email,
  "FO_ID"              AS fo_id,
  "LOCATION_ID"        AS location_id,
  "STATION_ID"         AS station_id,
  "SF_EMPLOYEE_ID"     AS sf_employee_id,
  "SF_PAYROLL_ID"      AS sf_payroll_id
FROM analytics_mirror_raw.dim_people;

DROP TABLE IF EXISTS analytics_mirror.dim_product;
CREATE VIEW analytics_mirror.dim_product AS
SELECT
  "PRODUCT_KEY"        AS product_key,
  "PRODUCT_NAME"       AS product_name,
  "SOURCE_PRODUCT_ID"  AS source_product_id,
  "SOURCE_SYSTEM"      AS source_system
FROM analytics_mirror_raw.dim_product;

-- Sanity check
SELECT 'fo_performance' AS view_name, count(*) FROM analytics_mirror.fo_performance
UNION ALL SELECT 'dim_client', count(*) FROM analytics_mirror.dim_client
UNION ALL SELECT 'dim_date', count(*) FROM analytics_mirror.dim_date
UNION ALL SELECT 'dim_exchange_rate', count(*) FROM analytics_mirror.dim_exchange_rate
UNION ALL SELECT 'dim_location', count(*) FROM analytics_mirror.dim_location
UNION ALL SELECT 'dim_people', count(*) FROM analytics_mirror.dim_people
UNION ALL SELECT 'dim_product', count(*) FROM analytics_mirror.dim_product;
