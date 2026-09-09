-- Run manually via pgAdmin/psql against the AWS RDS instance, as the
-- `wimbi` master user. NOT wired into local docker-compose or any Django
-- management command — analytics_mirror_raw (Airbyte's landing schema)
-- only exists on RDS. See _docs/aws_migration.md's "Airbyte connected;
-- landing-schema decision" entry for the reasoning.
--
-- Replaces the empty tables `ensure_analytics_tables` created with views
-- over what Airbyte lands in analytics_mirror_raw — no copy/transform
-- step, always current. Confirmed safe to leave ensure_analytics_tables
-- unchanged: information_schema.tables lists views alongside base tables,
-- so its "skip if already exists" check already treats these correctly.
--
-- Column-by-column, verified against real DESCRIBE VIEW output
-- (data/raw/snowflake.sql) and Airbyte's actual synced columns — not
-- guessed, same discipline analytics_mirror/models.py holds itself to.
--
-- NOT covered here: sf_employees (SFEmployee model) — no raw table synced
-- yet, nothing to build a view over. dim_client/dim_date/dim_exchange_rate/
-- dim_location/dim_people/dim_product/v_clients — synced by Airbyte but no
-- Django model reads them yet (bulk-uploader glossary entities, future
-- work) — not building views for tables nothing reads.

-- Replicates analytics_mirror/country_codes.py's _NAME_TO_ISO mapping and
-- fallback exactly. THESE TWO MUST BE KEPT IN SYNC BY HAND — there is no
-- way to call the Python function from a plain SQL view. If country_codes.py
-- ever changes, update this function to match.
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

-- ============================================================
-- Dimension tables: real integer PKs already present, straight rename.
-- ============================================================

DROP TABLE IF EXISTS analytics_mirror.dim_country;
CREATE VIEW analytics_mirror.dim_country AS
SELECT
  "COUNTRY_ID"          AS country_id,
  "COUNTRY_NAME"        AS country_name,
  "COUNTRY_CODE"        AS country_code,
  "COUNTRY_CODE3"       AS country_code3,
  "CURRENCY_NAME"       AS currency_name,
  "CURRENCY_CODE"       AS currency_code,
  "ODOO_COMPANY_ID"     AS odoo_company_id,
  "FINERACT_COUNTRY_ID" AS fineract_country_id,
  "SAP_COUNTRY_ID"      AS sap_country_id,
  "REGION"              AS region
FROM analytics_mirror_raw."DIM_COUNTRY";

DROP TABLE IF EXISTS analytics_mirror.dim_mcf;
CREATE VIEW analytics_mirror.dim_mcf AS
SELECT
  "MCF_ID"      AS mcf_id,
  "MCF_ABBREV"  AS mcf_abbrev,
  "MCF_NAME"    AS mcf_name,
  "DESCRIPTION" AS description
FROM analytics_mirror_raw."DIM_MCF";

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
FROM analytics_mirror_raw."DIM_PROGRAM";

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
FROM analytics_mirror_raw."DIM_SEASON";

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
FROM analytics_mirror_raw."DIM_SYSTEM";

-- ============================================================
-- Tables with a real natural key already present in source data.
-- ============================================================

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
FROM analytics_mirror_raw."BRIDGE_CLIENT_SOURCE_IDS";

DROP TABLE IF EXISTS analytics_mirror.v_client_reach;
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
FROM analytics_mirror_raw."V_CLIENT_REACH";

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
FROM analytics_mirror_raw."V_FO_PERFORMANCE";

-- ============================================================
-- Tables with no reliable natural key (per the models' own docstrings) -
-- id is a per-query ROW_NUMBER() over a deterministic sort, not a stable
-- identity across syncs. Verified safe for current usage (2026-09-09):
-- farmers/views.py only ever fetches these scoped to one farmer, ordered,
-- rendered once per request - id is used as a list key, never paginated
-- or deep-linked. JourneyEvent/SalesLine are registered in Django admin,
-- whose changelist paginates by this same order - a real but cosmetic
-- risk (a row could shuffle between two admin page loads on an exact
-- tie), not a data-integrity issue. LoanPortfolio/ProgramSummary/
-- RepaymentTransaction have no current consumers at all - re-check this
-- comment once Feature 5 (Program & Portfolio Dashboards) actually reads
-- them, since pagination-by-id assumptions may not hold by then.
-- ============================================================

DROP TABLE IF EXISTS analytics_mirror.v_client_journey;
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
FROM analytics_mirror_raw."V_CLIENT_JOURNEY";

DROP TABLE IF EXISTS analytics_mirror.sales_line;
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
  -- Raw LATITUDE/LONGITUDE synced as bigint - real GPS decimals would be
  -- truncated. Cast is here so the view at least matches the model's
  -- FloatField type; verify actual values before trusting map display -
  -- see the "real, not hypothetical" caveat this file's header points to.
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
FROM analytics_mirror_raw."V_SALES_DETAIL";

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
FROM analytics_mirror_raw."V_LOAN_PORTFOLIO";

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
FROM analytics_mirror_raw."V_PROGRAM_SUMMARY";

DROP TABLE IF EXISTS analytics_mirror.repayment_transaction;
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
FROM analytics_mirror_raw."V_REPAYMENT_ANALYSIS";

-- ============================================================
-- Sanity check - run after the above. Expect 12 rows, all > 0 except
-- whatever genuinely hasn't synced yet.
-- ============================================================
SELECT 'dim_country' AS view_name, count(*) FROM analytics_mirror.dim_country
UNION ALL SELECT 'dim_mcf', count(*) FROM analytics_mirror.dim_mcf
UNION ALL SELECT 'dim_program', count(*) FROM analytics_mirror.dim_program
UNION ALL SELECT 'dim_season', count(*) FROM analytics_mirror.dim_season
UNION ALL SELECT 'dim_system', count(*) FROM analytics_mirror.dim_system
UNION ALL SELECT 'bridge_client_source_ids', count(*) FROM analytics_mirror.bridge_client_source_ids
UNION ALL SELECT 'v_client_reach', count(*) FROM analytics_mirror.v_client_reach
UNION ALL SELECT 'fo_performance', count(*) FROM analytics_mirror.fo_performance
UNION ALL SELECT 'v_client_journey', count(*) FROM analytics_mirror.v_client_journey
UNION ALL SELECT 'sales_line', count(*) FROM analytics_mirror.sales_line
UNION ALL SELECT 'loan_portfolio', count(*) FROM analytics_mirror.loan_portfolio
UNION ALL SELECT 'program_summary', count(*) FROM analytics_mirror.program_summary
UNION ALL SELECT 'repayment_transaction', count(*) FROM analytics_mirror.repayment_transaction;
