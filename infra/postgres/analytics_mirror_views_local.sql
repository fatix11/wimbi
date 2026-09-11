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

DROP TABLE IF EXISTS analytics_mirror.loan_portfolio;
CREATE VIEW analytics_mirror.loan_portfolio AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "GL_CLIENT_ID", "DISBURSEMENT_DATE", "LOAN_ACCOUNT_NUMBER") AS id,
  "GL_CLIENT_ID"         AS gl_client_id,
  "CLIENT_NAME"          AS client_name,
  "GENDER"               AS gender,
  "PRIMARY_PROGRAM"      AS primary_program,
  "DISBURSEMENT_DATE"    AS disbursement_date,
  "DISBURSEMENT_YEAR"    AS disbursement_year,
  "DISBURSEMENT_QUARTER" AS disbursement_quarter,
  "DISBURSEMENT_MONTH"   AS disbursement_month,
  "YEAR_MONTH"           AS year_month,
  "COUNTRY"              AS country,
  "REGION"               AS region,
  "DISTRICT"             AS district,
  "SECTOR"               AS sector,
  "SITE"                 AS site,
  "SOURCE_LOAN_ID"       AS source_loan_id,
  "LOAN_ACCOUNT_NUMBER"  AS loan_account_number,
  "LOAN_NAME"            AS loan_name,
  "LOAN_TYPE"            AS loan_type,
  "LOAN_STATUS"          AS loan_status,
  "IS_DISBURSED"         AS is_disbursed,
  "IS_CLOSED"            AS is_closed,
  "GROUP_NAME"           AS group_name,
  "SOURCE_PRODUCT_ID"    AS source_product_id,
  "IS_AT_RISK"           AS is_at_risk,
  "PRINCIPAL_LCY"        AS principal_lcy,
  "PRINCIPAL_USD"        AS principal_usd,
  "REPAID_LCY"           AS repaid_lcy,
  "REPAID_USD"           AS repaid_usd,
  "OUTSTANDING_LCY"      AS outstanding_lcy,
  "OUTSTANDING_USD"      AS outstanding_usd,
  "TOTAL_REPAID_LCY"     AS total_repaid_lcy,
  "REPAYMENT_RATE_PCT"   AS repayment_rate_pct,
  "CURRENCY_CODE"        AS currency_code,
  "USD_EXCHANGE_RATE"    AS usd_exchange_rate,
  "APPROVED_AT"          AS approved_at,
  "DISBURSED_AT"         AS disbursed_at,
  "MATURED_AT"           AS matured_at,
  "DAYS_PAST_MATURITY"   AS days_past_maturity,
  "LOADED_AT"            AS loaded_at
FROM analytics_mirror_raw.v_loan_portfolio;

-- Sanity check (second pass)
SELECT 'dim_country' AS view_name, count(*) FROM analytics_mirror.dim_country
UNION ALL SELECT 'dim_mcf', count(*) FROM analytics_mirror.dim_mcf
UNION ALL SELECT 'dim_program', count(*) FROM analytics_mirror.dim_program
UNION ALL SELECT 'dim_season', count(*) FROM analytics_mirror.dim_season
UNION ALL SELECT 'dim_system', count(*) FROM analytics_mirror.dim_system
UNION ALL SELECT 'bridge_client_source_ids', count(*) FROM analytics_mirror.bridge_client_source_ids
UNION ALL SELECT 'program_summary', count(*) FROM analytics_mirror.program_summary
UNION ALL SELECT 'loan_portfolio', count(*) FROM analytics_mirror.loan_portfolio;

-- ============================================================
-- Third pass (2026-09-11, same session) - v_client_reach, v_client_journey,
-- repayment_transaction, sf_employees. Unlike the other tables in this
-- file, these had no raw copy to build from - nothing had been DBeaver-
-- copied down from AWS for them yet. Per explicit instruction, promoted
-- their EXISTING real local mirror data into new Snowflake-shaped raw
-- tables myself (via CREATE TABLE ... AS SELECT, reverse-mapping mirror's
-- lowercase columns to the real uppercase Snowflake names), verified the
-- row count survived the promotion unchanged, then only THEN dropped the
-- original table and rebuilt it as a view - so the real data was never at
-- risk, just relocated. sales_line/V_SALES_DETAIL is explicitly excluded
-- from this pass - local's copy (2.3M rows) is known incomplete against
-- the real ~12.78M, and a proper fix for that is still pending, not this.
--
-- One real limitation, not swept under the rug: v_client_reach and
-- v_client_journey's mirror data already had country_code NORMALIZED
-- (the original raw COUNTRY full name, e.g. "Malawi", was never stored
-- anywhere locally - only the ISO result, e.g. "MW"). The promoted raw
-- table's COUNTRY column holds that ISO code, not a true replica of the
-- original raw value. This isn't a functional problem - to_iso_country()
-- is idempotent on an already-ISO input (falls through to the "already a
-- code" branch, uppercases and returns it unchanged) - but it does mean
-- these two raw tables are an approximation, not a byte-perfect copy of
-- what a real Snowflake sync would produce. repayment_transaction has no
-- such gap - its country field was never normalized to begin with, so
-- that promotion is fully faithful.
--
-- sf_employees' raw column names are INFERRED, not verified against any
-- real source - no actual SF_EMPLOYEES raw table has ever existed
-- anywhere, AWS included (SuccessFactors was never connected via Airbyte).
-- Named to match this codebase's existing uppercase-snake convention for
-- consistency; correct these if a real raw sync of this source ever
-- happens and the actual column names turn out to differ.

CREATE TABLE analytics_mirror_raw.v_client_reach AS
SELECT
  gl_client_id             AS "GL_CLIENT_ID",
  full_name                AS "FULL_NAME",
  gender                   AS "GENDER",
  date_of_birth            AS "DATE_OF_BIRTH",
  country_code             AS "COUNTRY",
  primary_program          AS "PRIMARY_PROGRAM",
  primary_site             AS "PRIMARY_SITE",
  primary_source_system    AS "PRIMARY_SOURCE_SYSTEM",
  source_record_count      AS "SOURCE_RECORD_COUNT",
  is_singleton             AS "IS_SINGLETON",
  has_sale                 AS "HAS_SALE",
  has_loan                 AS "HAS_LOAN",
  has_purchase             AS "HAS_PURCHASE",
  is_multi_program         AS "IS_MULTI_PROGRAM",
  first_sale_date          AS "FIRST_SALE_DATE",
  last_sale_date           AS "LAST_SALE_DATE",
  total_orders             AS "TOTAL_ORDERS",
  programs_on_sale         AS "PROGRAMS_ON_SALE",
  seasons_with_oaf         AS "SEASONS_WITH_OAF",
  total_sales_lcy          AS "TOTAL_SALES_LCY",
  first_loan_date          AS "FIRST_LOAN_DATE",
  last_loan_date           AS "LAST_LOAN_DATE",
  total_loans              AS "TOTAL_LOANS",
  total_principal_lcy      AS "TOTAL_PRINCIPAL_LCY",
  total_repaid_lcy         AS "TOTAL_REPAID_LCY",
  total_outstanding_lcy    AS "TOTAL_OUTSTANDING_LCY",
  repayment_rate_pct       AS "REPAYMENT_RATE_PCT",
  first_purchase_date      AS "FIRST_PURCHASE_DATE",
  last_purchase_date       AS "LAST_PURCHASE_DATE",
  total_purchases          AS "TOTAL_PURCHASES",
  total_purchase_lcy       AS "TOTAL_PURCHASE_LCY",
  total_program_value_lcy  AS "TOTAL_PROGRAM_VALUE_LCY",
  onboarded_on             AS "ONBOARDED_ON",
  last_activity_date       AS "LAST_ACTIVITY_DATE",
  days_sale_to_loan        AS "DAYS_SALE_TO_LOAN",
  days_since_last_activity AS "DAYS_SINCE_LAST_ACTIVITY"
FROM analytics_mirror.v_client_reach;

DROP TABLE analytics_mirror.v_client_reach;
CREATE VIEW analytics_mirror.v_client_reach AS
SELECT
  "GL_CLIENT_ID"                    AS gl_client_id,
  "FULL_NAME"                       AS full_name,
  "GENDER"                          AS gender,
  "DATE_OF_BIRTH"                   AS date_of_birth,
  analytics_mirror.to_iso_country("COUNTRY") AS country_code,
  "PRIMARY_PROGRAM"                 AS primary_program,
  "PRIMARY_SITE"                    AS primary_site,
  "PRIMARY_SOURCE_SYSTEM"           AS primary_source_system,
  "SOURCE_RECORD_COUNT"             AS source_record_count,
  "IS_SINGLETON"                    AS is_singleton,
  "HAS_SALE"                        AS has_sale,
  "HAS_LOAN"                        AS has_loan,
  "HAS_PURCHASE"                    AS has_purchase,
  "IS_MULTI_PROGRAM"                AS is_multi_program,
  "FIRST_SALE_DATE"                 AS first_sale_date,
  "LAST_SALE_DATE"                  AS last_sale_date,
  "TOTAL_ORDERS"                    AS total_orders,
  "PROGRAMS_ON_SALE"                AS programs_on_sale,
  "SEASONS_WITH_OAF"                AS seasons_with_oaf,
  "TOTAL_SALES_LCY"                 AS total_sales_lcy,
  "FIRST_LOAN_DATE"                 AS first_loan_date,
  "LAST_LOAN_DATE"                  AS last_loan_date,
  "TOTAL_LOANS"                     AS total_loans,
  "TOTAL_PRINCIPAL_LCY"             AS total_principal_lcy,
  "TOTAL_REPAID_LCY"                AS total_repaid_lcy,
  "TOTAL_OUTSTANDING_LCY"           AS total_outstanding_lcy,
  "REPAYMENT_RATE_PCT"              AS repayment_rate_pct,
  "FIRST_PURCHASE_DATE"             AS first_purchase_date,
  "LAST_PURCHASE_DATE"              AS last_purchase_date,
  "TOTAL_PURCHASES"                 AS total_purchases,
  "TOTAL_PURCHASE_LCY"              AS total_purchase_lcy,
  "TOTAL_PROGRAM_VALUE_LCY"         AS total_program_value_lcy,
  "ONBOARDED_ON"                    AS onboarded_on,
  "LAST_ACTIVITY_DATE"              AS last_activity_date,
  "DAYS_SALE_TO_LOAN"               AS days_sale_to_loan,
  "DAYS_SINCE_LAST_ACTIVITY"        AS days_since_last_activity
FROM analytics_mirror_raw.v_client_reach;

CREATE TABLE analytics_mirror_raw.v_client_journey AS
SELECT
  gl_client_id    AS "GL_CLIENT_ID",
  client_name     AS "CLIENT_NAME",
  gender          AS "GENDER",
  country_code    AS "COUNTRY",
  primary_program AS "PRIMARY_PROGRAM",
  event_type      AS "EVENT_TYPE",
  program         AS "PROGRAM",
  event_date      AS "EVENT_DATE",
  line_count      AS "LINE_COUNT",
  amount_lcy      AS "AMOUNT_LCY",
  currency_code   AS "CURRENCY_CODE",
  is_credit       AS "IS_CREDIT",
  source_ref      AS "SOURCE_REF"
FROM analytics_mirror.v_client_journey;

DROP TABLE analytics_mirror.v_client_journey;
CREATE VIEW analytics_mirror.v_client_journey AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "GL_CLIENT_ID", "EVENT_DATE", "EVENT_TYPE", "SOURCE_REF") AS id,
  "GL_CLIENT_ID"                              AS gl_client_id,
  "CLIENT_NAME"                               AS client_name,
  "GENDER"                                    AS gender,
  analytics_mirror.to_iso_country("COUNTRY")  AS country_code,
  "PRIMARY_PROGRAM"                           AS primary_program,
  "EVENT_TYPE"                                AS event_type,
  "PROGRAM"                                   AS program,
  "EVENT_DATE"                                AS event_date,
  "LINE_COUNT"                                AS line_count,
  "AMOUNT_LCY"                                AS amount_lcy,
  "CURRENCY_CODE"                              AS currency_code,
  "IS_CREDIT"                                  AS is_credit,
  "SOURCE_REF"                                 AS source_ref
FROM analytics_mirror_raw.v_client_journey;

CREATE TABLE analytics_mirror_raw.v_repayment_analysis AS
SELECT
  gl_client_id          AS "GL_CLIENT_ID",
  client_name            AS "CLIENT_NAME",
  gender                  AS "GENDER",
  primary_program         AS "PRIMARY_PROGRAM",
  transaction_date        AS "TRANSACTION_DATE",
  year                    AS "YEAR",
  quarter                 AS "QUARTER",
  month_name              AS "MONTH_NAME",
  year_month              AS "YEAR_MONTH",
  country                 AS "COUNTRY",
  region                  AS "REGION",
  district                AS "DISTRICT",
  sector                  AS "SECTOR",
  site                    AS "SITE",
  account_type            AS "ACCOUNT_TYPE",
  transaction_type        AS "TRANSACTION_TYPE",
  payment_method          AS "PAYMENT_METHOD",
  payment_type_raw        AS "PAYMENT_TYPE_RAW",
  amount_lcy              AS "AMOUNT_LCY",
  cumulative_amount_lcy   AS "CUMULATIVE_AMOUNT_LCY",
  account_principal_lcy   AS "ACCOUNT_PRINCIPAL_LCY",
  payment_direction       AS "PAYMENT_DIRECTION",
  source_transaction_id   AS "SOURCE_TRANSACTION_ID",
  source_loan_id          AS "SOURCE_LOAN_ID",
  account_number          AS "ACCOUNT_NUMBER",
  receipt_number          AS "RECEIPT_NUMBER",
  repayment_phone         AS "REPAYMENT_PHONE",
  loaded_at               AS "LOADED_AT"
FROM analytics_mirror.repayment_transaction;

DROP TABLE analytics_mirror.repayment_transaction;
CREATE VIEW analytics_mirror.repayment_transaction AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "GL_CLIENT_ID", "TRANSACTION_DATE", "SOURCE_TRANSACTION_ID") AS id,
  "GL_CLIENT_ID"          AS gl_client_id,
  "CLIENT_NAME"           AS client_name,
  "GENDER"                AS gender,
  "PRIMARY_PROGRAM"       AS primary_program,
  "TRANSACTION_DATE"      AS transaction_date,
  "YEAR"                  AS year,
  "QUARTER"               AS quarter,
  "MONTH_NAME"            AS month_name,
  "YEAR_MONTH"            AS year_month,
  "COUNTRY"               AS country,
  "REGION"                AS region,
  "DISTRICT"              AS district,
  "SECTOR"                AS sector,
  "SITE"                  AS site,
  "ACCOUNT_TYPE"          AS account_type,
  "TRANSACTION_TYPE"      AS transaction_type,
  "PAYMENT_METHOD"        AS payment_method,
  "PAYMENT_TYPE_RAW"      AS payment_type_raw,
  "AMOUNT_LCY"            AS amount_lcy,
  "CUMULATIVE_AMOUNT_LCY" AS cumulative_amount_lcy,
  "ACCOUNT_PRINCIPAL_LCY" AS account_principal_lcy,
  "PAYMENT_DIRECTION"     AS payment_direction,
  "SOURCE_TRANSACTION_ID" AS source_transaction_id,
  "SOURCE_LOAN_ID"        AS source_loan_id,
  "ACCOUNT_NUMBER"        AS account_number,
  "RECEIPT_NUMBER"        AS receipt_number,
  "REPAYMENT_PHONE"       AS repayment_phone,
  "LOADED_AT"             AS loaded_at
FROM analytics_mirror_raw.v_repayment_analysis;

CREATE TABLE analytics_mirror_raw.sf_employees AS
SELECT
  email              AS "EMAIL",
  full_name          AS "FULL_NAME",
  department_code    AS "DEPARTMENT_CODE",
  department_name    AS "DEPARTMENT_NAME",
  location_code      AS "LOCATION_CODE",
  location_name      AS "LOCATION_NAME",
  work_location      AS "WORK_LOCATION",
  country_code       AS "COUNTRY_CODE",
  country_name       AS "COUNTRY_NAME",
  is_active          AS "IS_ACTIVE",
  last_updated_date  AS "LAST_UPDATED_DATE"
FROM analytics_mirror.sf_employees;

DROP TABLE analytics_mirror.sf_employees;
CREATE VIEW analytics_mirror.sf_employees AS
SELECT
  "EMAIL"             AS email,
  "FULL_NAME"         AS full_name,
  "DEPARTMENT_CODE"   AS department_code,
  "DEPARTMENT_NAME"   AS department_name,
  "LOCATION_CODE"     AS location_code,
  "LOCATION_NAME"     AS location_name,
  "WORK_LOCATION"     AS work_location,
  "COUNTRY_CODE"      AS country_code,
  "COUNTRY_NAME"      AS country_name,
  "IS_ACTIVE"         AS is_active,
  "LAST_UPDATED_DATE" AS last_updated_date
FROM analytics_mirror_raw.sf_employees;

-- Sanity check (third pass)
SELECT 'v_client_reach' AS view_name, count(*) FROM analytics_mirror.v_client_reach
UNION ALL SELECT 'v_client_journey', count(*) FROM analytics_mirror.v_client_journey
UNION ALL SELECT 'repayment_transaction', count(*) FROM analytics_mirror.repayment_transaction
UNION ALL SELECT 'sf_employees', count(*) FROM analytics_mirror.sf_employees;

-- ============================================================
-- Fourth pass (2026-09-12) - sales_line, finally. Explicitly excluded
-- from every earlier pass since local's old copy (2,301,490 rows) was
-- known incomplete against the real ~12.78M total in V_SALES_DETAIL, and
-- a proper fix was pending rather than something to paper over.
--
-- The fix: a new Snowflake view built specifically for this, sampling by
-- a deliberately bounded gl_client_id range (MW-00000001 to MW-00199999)
-- rather than an arbitrary/random cut - 1,809,577 rows, 155,886 distinct
-- clients, 11.61 lines/client average, zero nulls on GL_CLIENT_ID or
-- SOURCE_TRANSACTION_ID. Complete within its stated boundary, verified
-- before touching anything, not assumed from the row count alone.
--
-- Real bonus found while verifying: LATITUDE/LONGITUDE here are native
-- double precision, not the bigint-truncated version the original
-- Airbyte-synced V_SALES_DETAIL carried (see the third-pass comment on
-- dim_location, and sales_line's own docstring) - this sample sidesteps
-- that precision-loss issue entirely. The ::float8 cast below is now a
-- no-op for this source, kept only so the SQL still works unchanged if
-- raw sales_line data ever gets swapped back to a bigint-typed source.
--
-- Old table had 2,301,490 rows; this replaces it with 1,809,577 - fewer
-- total rows, but complete/coherent within its boundary rather than an
-- unclear partial cut, which is what actually matters for feature work.
-- ============================================================

DROP TABLE analytics_mirror.sales_line;
CREATE VIEW analytics_mirror.sales_line AS
SELECT
  ROW_NUMBER() OVER (ORDER BY "GL_CLIENT_ID", "SALE_DATE", "SOURCE_ORDER_ID", "PRODUCT_NAME") AS id,
  "GL_CLIENT_ID"                     AS gl_client_id,
  "CLIENT_NAME"                      AS client_name,
  "GENDER"                           AS gender,
  "CLIENT_PRIMARY_PROGRAM"           AS client_primary_program,
  "SALE_DATE"                        AS sale_date,
  "SALE_YEAR"                        AS sale_year,
  "SALE_QUARTER"                     AS sale_quarter,
  "SALE_MONTH"                       AS sale_month,
  "YEAR_MONTH"                       AS year_month,
  "SEASON"                           AS season,
  "DERIVED_SEASON"                   AS derived_season,
  analytics_mirror.to_iso_country("COUNTRY") AS country_code,
  "REGION"                           AS region,
  "DISTRICT"                         AS district,
  "SECTOR"                           AS sector,
  "SITE"                             AS site,
  "LOC_TYPE"                         AS loc_type,
  "LATITUDE"::float8                 AS latitude,
  "LONGITUDE"::float8                AS longitude,
  "LOC_PARENTS"                      AS loc_parents,
  "PROGRAM"                          AS program,
  "SOURCE_SYSTEM"                    AS source_system,
  "SALE_CHANNEL"                     AS sale_channel,
  "ORDER_TYPE"                       AS order_type,
  "PAYMENT_TYPE"                     AS payment_type,
  "IS_CREDIT"                        AS is_credit,
  "FULFILLMENT_STATUS"               AS fulfillment_status,
  "PRODUCT_NAME"                     AS product_name,
  "PRODUCT_CATEGORY"                 AS product_category,
  "QUANTITY"                         AS quantity,
  "FIELD_OFFICER"                    AS field_officer,
  "SHOPKEEPER"                       AS shopkeeper,
  "NURSERY_MANAGER"                  AS nursery_manager,
  "UNIT_PRICE_LCY"                   AS unit_price_lcy,
  "TOTAL_PRICE_LCY"                  AS total_price_lcy,
  "TOTAL_ORDER_PRICE_LCY"            AS total_order_price_lcy,
  "TOTAL_PRICE_USD"                  AS total_price_usd,
  "CURRENCY_CODE"                    AS currency_code,
  "USD_RATE"                         AS usd_rate,
  "SAP_USD_RATE"                     AS sap_usd_rate,
  "RATE_EXACT_MATCH"                 AS rate_exact_match,
  "REVENUE_LCY"                      AS revenue_lcy,
  "REVENUE_USD"                      AS revenue_usd,
  "LOCATION_KEY"                     AS location_key,
  "PRODUCT_KEY"                      AS product_key,
  "FIELD_OFFICER_KEY"                AS field_officer_key,
  "SHOPKEEPER_KEY"                   AS shopkeeper_key,
  "NURSERY_MGR_KEY"                  AS nursery_mgr_key,
  "SOURCE_TRANSACTION_ID"            AS source_transaction_id,
  "SOURCE_ORDER_ID"                  AS source_order_id,
  "SOURCE_LOAN_ID"                   AS source_loan_id,
  "CREATED_AT"                       AS created_at,
  "FULFILLED_AT"                     AS fulfilled_at,
  "LOADED_AT"                        AS loaded_at
FROM analytics_mirror_raw.v_sales_detail_sample;

-- Sanity check (fourth pass)
SELECT 'sales_line' AS view_name, count(*) FROM analytics_mirror.sales_line;
