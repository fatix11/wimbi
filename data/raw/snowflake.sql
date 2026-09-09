select *
from analytics.reporting.v_sales_detail
where gl_client_id = '<a real gl_client_id, e.g. from a known UAT farmer>';

-- Schema discovery for the 4 REPORTING views not yet mirrored into Wimbi's
-- Postgres (see _docs/architectural_decisions.md ADR-010's 2026-09-02
-- update, jira-backlog.md EPIC P2). DESCRIBE gives column name/type/null;
-- the sample rows are just as important — real data has surprised us
-- before (no phone column on V_CLIENT_REACH, BRIDGE_ID as a real PK,
-- filenames not matching content) so don't trust the column list alone.
--
-- REDACTED 2026-09-09: this file originally had real `limit 5` sample rows
-- pasted in alongside each DESCRIBE — several contained real farmer names,
-- phone numbers, and staff names (V_LOAN_PORTFOLIO, V_REPAYMENT_ANALYSIS,
-- V_FO_PERFORMANCE). Scrubbed from git history entirely (git filter-repo)
-- before this repo was first pushed anywhere. Schema/column info and the
-- aggregate row-count query below are unchanged — nothing here was ever
-- about the schema itself, only about not keeping real people's data in
-- git history indefinitely. If sample rows are needed again for future
-- schema discovery, keep them local-only (a gitignored file), never
-- committed.

describe view analytics.reporting.v_loan_portfolio;
name	type	kind	null?	default	primary key	unique key	check	expression	comment	policy name	privacy domain	write default
DISBURSEMENT_DATE	DATE	COLUMN	Y		N	N
DISBURSEMENT_YEAR	NUMBER(4,0)	COLUMN	Y		N	N
DISBURSEMENT_QUARTER	VARCHAR(16777216)	COLUMN	Y		N	N
DISBURSEMENT_MONTH	VARCHAR(16777216)	COLUMN	Y		N	N
YEAR_MONTH	VARCHAR(16777216)	COLUMN	Y		N	N
COUNTRY	VARCHAR(16777216)	COLUMN	Y		N	N
REGION	VARCHAR(16777216)	COLUMN	Y		N	N
DISTRICT	VARCHAR(16777216)	COLUMN	Y		N	N
SECTOR	VARCHAR(16777216)	COLUMN	Y		N	N
SITE	VARCHAR(16777216)	COLUMN	Y		N	N
GL_CLIENT_ID	VARCHAR(30)	COLUMN	Y		N	N
CLIENT_NAME	VARCHAR(200)	COLUMN	Y		N	N
GENDER	VARCHAR(5)	COLUMN	Y		N	N
PRIMARY_PROGRAM	VARCHAR(50)	COLUMN	Y		N	N
SOURCE_LOAN_ID	NUMBER(38,0)	COLUMN	Y		N	N
LOAN_ACCOUNT_NUMBER	VARCHAR(16777216)	COLUMN	Y		N	N
LOAN_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
LOAN_TYPE	VARCHAR(16777216)	COLUMN	Y		N	N
LOAN_STATUS	VARCHAR(16777216)	COLUMN	Y		N	N
IS_DISBURSED	BOOLEAN	COLUMN	Y		N	N
IS_CLOSED	BOOLEAN	COLUMN	Y		N	N
GROUP_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
SOURCE_PRODUCT_ID	NUMBER(38,0)	COLUMN	Y		N	N
IS_AT_RISK	BOOLEAN	COLUMN	Y		N	N
PRINCIPAL_LCY	FLOAT	COLUMN	Y		N	N
PRINCIPAL_USD	FLOAT	COLUMN	Y		N	N
REPAID_LCY	FLOAT	COLUMN	Y		N	N
REPAID_USD	FLOAT	COLUMN	Y		N	N
OUTSTANDING_LCY	FLOAT	COLUMN	Y		N	N
OUTSTANDING_USD	FLOAT	COLUMN	Y		N	N
TOTAL_REPAID_LCY	FLOAT	COLUMN	Y		N	N
REPAYMENT_RATE_PCT	FLOAT	COLUMN	Y		N	N
CURRENCY_CODE	VARCHAR(16777216)	COLUMN	Y		N	N
USD_EXCHANGE_RATE	FLOAT	COLUMN	Y		N	N
APPROVED_AT	DATE	COLUMN	Y		N	N
DISBURSED_AT	DATE	COLUMN	Y		N	N
MATURED_AT	DATE	COLUMN	Y		N	N
DAYS_PAST_MATURITY	NUMBER(9,0)	COLUMN	Y		N	N
LOADED_AT	TIMESTAMP_LTZ(9)	COLUMN	Y		N	N
;select * from analytics.reporting.v_loan_portfolio limit 5;
-- [real sample rows redacted 2026-09-09 — contained real farmer names/ids]

describe view analytics.reporting.v_program_summary;
name	type	kind	null?	default	primary key	unique key	check	expression	comment	policy name	privacy domain	write default
YEAR_MONTH	VARCHAR(16777216)	COLUMN	Y		N	N
YEAR	NUMBER(4,0)	COLUMN	Y		N	N
MONTH_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
MONTH	NUMBER(2,0)	COLUMN	Y		N	N
COUNTRY	VARCHAR(16777216)	COLUMN	Y		N	N
PROGRAM	VARCHAR(6)	COLUMN	Y		N	N
PROGRAM_OAF_EQ	VARCHAR(16777216)	COLUMN	Y		N	N
PROGRAM_LOCAL_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
MATURITY_SCORE	NUMBER(38,0)	COLUMN	Y		N	N
IS_SEASONAL	BOOLEAN	COLUMN	Y		N	N
HAS_GROUPS	BOOLEAN	COLUMN	Y		N	N
MCF_PA	BOOLEAN	COLUMN	Y		N	N
MCF_IN	BOOLEAN	COLUMN	Y		N	N
MCF_SH	BOOLEAN	COLUMN	Y		N	N
MCF_FT	BOOLEAN	COLUMN	Y		N	N
MCF_TT	BOOLEAN	COLUMN	Y		N	N
MCF_FVC	BOOLEAN	COLUMN	Y		N	N
MCF_PES	BOOLEAN	COLUMN	Y		N	N
UNIQUE_CLIENTS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_ORDERS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_SALE_LINES	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_SALES_LCY	FLOAT	COLUMN	Y		N	N
TOTAL_SALES_USD	FLOAT	COLUMN	Y		N	N
CURRENCY_CODE	VARCHAR(16777216)	COLUMN	Y		N	N
;select * from analytics.reporting.v_program_summary limit 5;
-- [real sample rows redacted 2026-09-09 — program/month aggregates, lower
-- sensitivity than the others but scrubbed uniformly for consistency]

describe view analytics.reporting.v_repayment_analysis;
name	type	kind	null?	default	primary key	unique key	check	expression	comment	policy name	privacy domain	write default
TRANSACTION_DATE	DATE	COLUMN	Y		N	N
YEAR	NUMBER(4,0)	COLUMN	Y		N	N
QUARTER	VARCHAR(16777216)	COLUMN	Y		N	N
MONTH_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
YEAR_MONTH	VARCHAR(16777216)	COLUMN	Y		N	N
COUNTRY	VARCHAR(16777216)	COLUMN	Y		N	N
REGION	VARCHAR(16777216)	COLUMN	Y		N	N
DISTRICT	VARCHAR(16777216)	COLUMN	Y		N	N
SECTOR	VARCHAR(16777216)	COLUMN	Y		N	N
SITE	VARCHAR(16777216)	COLUMN	Y		N	N
GL_CLIENT_ID	VARCHAR(30)	COLUMN	Y		N	N
CLIENT_NAME	VARCHAR(200)	COLUMN	Y		N	N
GENDER	VARCHAR(5)	COLUMN	Y		N	N
PRIMARY_PROGRAM	VARCHAR(50)	COLUMN	Y		N	N
ACCOUNT_TYPE	VARCHAR(11)	COLUMN	Y		N	N
TRANSACTION_TYPE	VARCHAR(16777216)	COLUMN	Y		N	N
PAYMENT_METHOD	VARCHAR(16777216)	COLUMN	Y		N	N
PAYMENT_TYPE_RAW	VARCHAR(16777216)	COLUMN	Y		N	N
AMOUNT_LCY	FLOAT	COLUMN	Y		N	N
CUMULATIVE_AMOUNT_LCY	FLOAT	COLUMN	Y		N	N
ACCOUNT_PRINCIPAL_LCY	FLOAT	COLUMN	Y		N	N
PAYMENT_DIRECTION	VARCHAR(10)	COLUMN	Y		N	N
SOURCE_TRANSACTION_ID	NUMBER(38,0)	COLUMN	Y		N	N
SOURCE_LOAN_ID	NUMBER(38,0)	COLUMN	Y		N	N
ACCOUNT_NUMBER	VARCHAR(16777216)	COLUMN	Y		N	N
RECEIPT_NUMBER	VARCHAR(16777216)	COLUMN	Y		N	N
REPAYMENT_PHONE	VARCHAR(16777216)	COLUMN	Y		N	N
LOADED_AT	TIMESTAMP_LTZ(9)	COLUMN	Y		N	N
;select * from analytics.reporting.v_repayment_analysis limit 5;
-- [real sample rows redacted 2026-09-09 — contained real farmer names,
-- ids, and phone numbers]

describe view analytics.reporting.v_fo_performance;
name	type	kind	null?	default	primary key	unique key	check	expression	comment	policy name	privacy domain	write default
FO_KEY	VARCHAR(32)	COLUMN	Y		N	N
FO_NAME	VARCHAR(16777216)	COLUMN	Y		N	N
COUNTRY	VARCHAR(16777216)	COLUMN	Y		N	N
FO_ID	VARCHAR(16777216)	COLUMN	Y		N	N
UNIQUE_CLIENTS	NUMBER(18,0)	COLUMN	Y		N	N
LOAN_CLIENTS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_LOANS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_PRINCIPAL_LCY	FLOAT	COLUMN	Y		N	N
TOTAL_REPAID_LCY	FLOAT	COLUMN	Y		N	N
TOTAL_OUTSTANDING_LCY	FLOAT	COLUMN	Y		N	N
PORTFOLIO_REPAYMENT_RATE_PCT	FLOAT	COLUMN	Y		N	N
AT_RISK_LOANS	NUMBER(18,0)	COLUMN	Y		N	N
AT_RISK_OUTSTANDING_LCY	FLOAT	COLUMN	Y		N	N
SALE_CLIENTS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_ORDERS	NUMBER(18,0)	COLUMN	Y		N	N
TOTAL_SALES_LCY	FLOAT	COLUMN	Y		N	N
PROGRAMS_COVERED	NUMBER(18,0)	COLUMN	Y		N	N
;select * from analytics.reporting.v_fo_performance limit 5;
-- [real sample rows redacted 2026-09-09 — contained real field officer names]

-- Also worth confirming while we're in here: how many total rows exist in
-- each, so loading/DBeaver-transfer expectations are set correctly.
;select 'v_loan_portfolio' as view_name, count(*) from analytics.reporting.v_loan_portfolio
union all
select 'v_program_summary', count(*) from analytics.reporting.v_program_summary
union all
select 'v_repayment_analysis', count(*) from analytics.reporting.v_repayment_analysis
union all
select 'v_fo_performance', count(*) from analytics.reporting.v_fo_performance
union all
select 'v_sales_detail (Malawi)', count(*) from analytics.reporting.v_sales_detail;
VIEW_NAME	COUNT(*)
v_loan_portfolio	410783
v_program_summary	62
v_repayment_analysis	4321246
v_fo_performance	560
v_sales_detail (Malawi)	12776927;

select * from analytics.reporting.v_loan_portfolio;
select * from analytics.reporting.v_program_summary;
select * from analytics.reporting.v_repayment_analysis;
select * from analytics.reporting.v_fo_performance;
select * from analytics.reporting.v_sales_detail;

describe view analytics.reporting.v_sales_detail;
name	type
SALE_DATE	DATE
SALE_YEAR	NUMBER(4,0)
SALE_QUARTER	VARCHAR(16777216)
SALE_MONTH	VARCHAR(16777216)
YEAR_MONTH	VARCHAR(16777216)
COUNTRY	VARCHAR(16777216)
REGION	VARCHAR(16777216)
DISTRICT	VARCHAR(16777216)
SECTOR	VARCHAR(16777216)
SITE	VARCHAR(16777216)
LOC_TYPE	VARCHAR(7)
LATITUDE	NUMBER(38,0)
LONGITUDE	NUMBER(38,0)
GEOPOINT	VARCHAR(4194304)
LOC_PARENTS	VARCHAR(16777216)
PROGRAM	VARCHAR(6)
SOURCE_SYSTEM	VARCHAR(4)
SALE_CHANNEL	VARCHAR(16777216)
ORDER_TYPE	VARCHAR(5)
PAYMENT_TYPE	VARCHAR(16777216)
IS_CREDIT	BOOLEAN
FULFILLMENT_STATUS	VARCHAR(16777216)
PRODUCT_NAME	VARCHAR(16777216)
PRODUCT_CATEGORY	VARCHAR(16777216)
GL_CLIENT_ID	VARCHAR(30)
CLIENT_NAME	VARCHAR(200)
GENDER	VARCHAR(5)
CLIENT_PRIMARY_PROGRAM	VARCHAR(50)
FIELD_OFFICER	VARCHAR(16777216)
SHOPKEEPER	VARCHAR(16777216)
NURSERY_MANAGER	VARCHAR(16777216)
QUANTITY	FLOAT
UNIT_PRICE_LCY	FLOAT
TOTAL_PRICE_LCY	FLOAT
TOTAL_ORDER_PRICE_LCY	FLOAT
TOTAL_PRICE_USD	FLOAT
CURRENCY_CODE	VARCHAR(16777216)
USD_RATE	FLOAT
SAP_USD_RATE	FLOAT
RATE_EXACT_MATCH	BOOLEAN
REVENUE_LCY	FLOAT
REVENUE_USD	FLOAT
SEASON	VARCHAR(16777216)
DERIVED_SEASON	VARCHAR(16777216)
LOCATION_KEY	VARCHAR(32)
PRODUCT_KEY	VARCHAR(32)
FIELD_OFFICER_KEY	VARCHAR(16777216)
SHOPKEEPER_KEY	VARCHAR(16777216)
NURSERY_MGR_KEY	VARCHAR(16777216)
SOURCE_TRANSACTION_ID	VARCHAR(16777216)
SOURCE_ORDER_ID	VARCHAR(16777216)
SOURCE_LOAN_ID	VARCHAR(16777216)
CREATED_AT	TIMESTAMP_NTZ(9)
FULFILLED_AT	TIMESTAMP_NTZ(9)
LOADED_AT	TIMESTAMP_LTZ(9)
