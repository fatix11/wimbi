-- Local counterpart to infra/postgres/analytics_mirror_views.sql (the AWS
-- version). Same idea - analytics_mirror_raw is the landing zone,
-- analytics_mirror holds views translating it to what Django expects -
-- but NOT the same SQL verbatim: DBeaver landed local raw tables
-- unquoted/lowercase (analytics_mirror_raw.dim_client, not
-- analytics_mirror_raw."DIM_CLIENT" the way Airbyte does on AWS), even
-- though the column names inside came through quoted-uppercase, same as
-- AWS. Table-name casing differs by source tool; column casing doesn't.
--
-- First pass, deliberately narrow: only tables where no existing real
-- local data was at risk. fo_performance's existing table was empty
-- (0 rows) so converting it to a view was safe; the six DIM_* tables are
-- brand new Django models with nothing to lose. dim_country, dim_mcf,
-- dim_program, dim_season, dim_system, bridge_client_source_ids and
-- program_summary were deliberately left alone here, since they already
-- had real local data as physical tables - converting those needed an
-- explicit decision, not a side effect of this pass. That decision came
-- (yes, convert all 7) - see the second section further down.
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

-- Sanity check (first pass - fo_performance + the 6 new entities)
SELECT 'fo_performance' AS view_name, count(*) FROM analytics_mirror.fo_performance
UNION ALL SELECT 'dim_client', count(*) FROM analytics_mirror.dim_client
UNION ALL SELECT 'dim_date', count(*) FROM analytics_mirror.dim_date
UNION ALL SELECT 'dim_exchange_rate', count(*) FROM analytics_mirror.dim_exchange_rate
UNION ALL SELECT 'dim_location', count(*) FROM analytics_mirror.dim_location
UNION ALL SELECT 'dim_people', count(*) FROM analytics_mirror.dim_people
UNION ALL SELECT 'dim_product', count(*) FROM analytics_mirror.dim_product;

-- ============================================================
-- Second pass (2026-09-11, same session) - converting the 7 tables that
-- were deliberately left alone above, now that the user explicitly
-- confirmed it: drop the existing real physical tables and rebuild as
-- views over their now-loaded raw copies, for full architecture parity
-- with AWS. All 7 already have a Django model - see analytics_mirror/
-- models.py, nothing new to add there.
-- ============================================================

-- Country-name-to-ISO normalization, now created locally too - closes
-- the divergence local_vs_cloud.md flagged (this function previously
-- existed only on AWS). Identical to infra/postgres/analytics_mirror_views.sql's
-- version, which itself replicates analytics_mirror/country_codes.py by
-- hand - all three must be kept in sync manually, there's no way to call
-- the Python version from SQL.
CREATE OR REPLACE FUNCTION analytics_mirror.to_iso_country(country_name text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE
    WHEN country_name IS NULL OR trim(country_name) = '' THEN ''
    ELSE COALESCE(
      (CASE lower(trim(country_name))
        WHEN 'malawi' THEN 'MW'
        WHEN 'kenya' THEN 'KE'
        WHEN 'rwanda' THEN 'RW'
        WHEN 'zambia' THEN 'ZM'
        WHEN 'tanzania' THEN 'TZ'
        WHEN 'uganda' THEN 'UG'
        WHEN 'nigeria' THEN 'NG'
        WHEN 'ethiopia' THEN 'ET'
        WHEN 'democratic republic of congo' THEN 'CD'
        WHEN 'drc' THEN 'CD'
        WHEN 'burundi' THEN 'BI'
        WHEN 'ghana' THEN 'GH'
        WHEN 'rw-tbr' THEN 'RW'
        WHEN 'eth' THEN 'ET'
      END),
      upper(trim(country_name))
    )
  END;
$$;

-- dim_country's raw copy landed lowercase-cased (the one anomaly flagged
-- earlier) - happened to land already matching Django's expected column
-- names exactly, so no aliasing is needed at all here, unlike every
-- other view in this file. Confirmed by direct column check before
-- writing this, not assumed from the anomaly note alone.
DROP TABLE IF EXISTS analytics_mirror.dim_country;
CREATE VIEW analytics_mirror.dim_country AS
SELECT * FROM analytics_mirror_raw.dim_country;

DROP TABLE IF EXISTS analytics_mirror.dim_mcf;
CREATE VIEW analytics_mirror.dim_mcf AS
SELECT
  "MCF_ID"      AS mcf_id,
  "MCF_ABBREV"  AS mcf_abbrev,
  "MCF_NAME"    AS mcf_name,
  "DESCRIPTION" AS description
FROM analytics_mirror_raw.dim_mcf;

DROP TABLE IF EXISTS analytics_mirror.dim_program;
CREATE VIEW analytics_mirror.dim_program AS
SELECT
  "PROGRAM_ID"            AS program_id,
  "COUNTRY_CODE"          AS country_code,
  "COUNTRY_NAME"          AS country_name,
  "PROGRAM_LOCAL_NAME"    AS program_local_name,
  "PROGRAM_OAF_EQ"        AS program_oaf_eq,
  "MATURITY_SCORE"        AS maturity_score,
  "IS_SEASONAL"           AS is_seasonal,
  "HAS_GROUPS"            AS has_groups,
  "CROSS_PROGRAM_ID_TYPE" AS cross_program_id_type,
  "PHONE_QUALITY"         AS phone_quality,
  "CLIENT_DEFINITION"     AS client_definition,
  "MCF_PA"  AS mcf_pa,
  "MCF_IN"  AS mcf_in,
  "MCF_SH"  AS mcf_sh,
  "MCF_FT"  AS mcf_ft,
  "MCF_TT"  AS mcf_tt,
  "MCF_FVC" AS mcf_fvc,
  "MCF_PES" AS mcf_pes
FROM analytics_mirror_raw.dim_program;

DROP TABLE IF EXISTS analytics_mirror.dim_season;
CREATE VIEW analytics_mirror.dim_season AS
SELECT
  "SEASON_ID"         AS season_id,
  "COUNTRY_CODE"       AS country_code,
  "SEASON_NAME"        AS season_name,
  "LOCAL_NAME"         AS local_name,
  "RAINFALL_TYPE"      AS rainfall_type,
  "SEASON_LABEL"       AS season_label,
  "SEASON_YEAR"        AS season_year,
  "SEASON_YEAR_LABEL"  AS season_year_label,
  "START_MONTH"        AS start_month,
  "END_MONTH"          AS end_month,
  "CROSSES_YEAR"       AS crosses_year,
  "IS_PRIMARY"         AS is_primary,
  "START_DATE"         AS start_date,
  "END_DATE"           AS end_date
FROM analytics_mirror_raw.dim_season;

DROP TABLE IF EXISTS analytics_mirror.dim_system;
CREATE VIEW analytics_mirror.dim_system AS
SELECT
  "SYSTEM_ID"          AS system_id,
  "COUNTRY_CODE"       AS country_code,
  "COUNTRY_NAME"       AS country_name,
  "PROGRAM_LOCAL_NAME" AS program_local_name,
  "PROGRAM_CANONICAL"  AS program_canonical,
  "SYSTEM_NAME"        AS system_name,
  "CLIENT_DEFINITION"  AS client_definition
FROM analytics_mirror_raw.dim_system;

DROP TABLE IF EXISTS analytics_mirror.bridge_client_source_ids;
CREATE VIEW analytics_mirror.bridge_client_source_ids AS
SELECT
  "BRIDGE_ID"                                        AS bridge_id,
  "GL_CLIENT_ID"                                     AS gl_client_id,
  "SOURCE_SYSTEM"                                    AS source_system,
  "SOURCE_PROGRAM"                                   AS source_program,
  "SOURCE_CLIENT_ID"                                 AS source_client_id,
  analytics_mirror.to_iso_country("SOURCE_COUNTRY")  AS source_country_code,
  "SOURCE_FIDELITY"                                  AS source_fidelity,
  "IS_SINGLETON"                                     AS is_singleton,
  "MATCH_CONFIDENCE"                                  AS match_confidence,
  "MATCH_METHOD"                                      AS match_method,
  "LINKED_AT_TS"                                      AS linked_at_ts
FROM analytics_mirror_raw.bridge_client_source_ids;

DROP TABLE IF EXISTS analytics_mirror.program_summary;
CREATE VIEW analytics_mirror.program_summary AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "YEAR_MONTH", "COUNTRY", "PROGRAM") AS id,
  "YEAR_MONTH"         AS year_month,
  "YEAR"                AS year,
  "MONTH_NAME"          AS month_name,
  "MONTH"               AS month,
  "COUNTRY"             AS country,
  "PROGRAM"             AS program,
  "PROGRAM_OAF_EQ"      AS program_oaf_eq,
  "PROGRAM_LOCAL_NAME"  AS program_local_name,
  "MATURITY_SCORE"      AS maturity_score,
  "IS_SEASONAL"         AS is_seasonal,
  "HAS_GROUPS"          AS has_groups,
  "MCF_PA"  AS mcf_pa,
  "MCF_IN"  AS mcf_in,
  "MCF_SH"  AS mcf_sh,
  "MCF_FT"  AS mcf_ft,
  "MCF_TT"  AS mcf_tt,
  "MCF_FVC" AS mcf_fvc,
  "MCF_PES" AS mcf_pes,
  "UNIQUE_CLIENTS"   AS unique_clients,
  "TOTAL_ORDERS"     AS total_orders,
  "TOTAL_SALE_LINES" AS total_sale_lines,
  "TOTAL_SALES_LCY"  AS total_sales_lcy,
  "TOTAL_SALES_USD"  AS total_sales_usd,
  "CURRENCY_CODE"    AS currency_code
FROM analytics_mirror_raw.v_program_summary;

-- Sanity check (second pass)
SELECT 'dim_country' AS view_name, count(*) FROM analytics_mirror.dim_country
UNION ALL SELECT 'dim_mcf', count(*) FROM analytics_mirror.dim_mcf
UNION ALL SELECT 'dim_program', count(*) FROM analytics_mirror.dim_program
UNION ALL SELECT 'dim_season', count(*) FROM analytics_mirror.dim_season
UNION ALL SELECT 'dim_system', count(*) FROM analytics_mirror.dim_system
UNION ALL SELECT 'bridge_client_source_ids', count(*) FROM analytics_mirror.bridge_client_source_ids
UNION ALL SELECT 'program_summary', count(*) FROM analytics_mirror.program_summary;
