-- Run manually via Adminer/pgAdmin against the RDS `wimbi` database.
-- Lives in `public`, not `analytics_mirror` - this is documentation ABOUT
-- the mirror, not mirrored data itself, and should survive independently
-- of whatever churn happens to analytics_mirror's views over time (see
-- analytics_mirror_views.sql and its DROP TABLE/CREATE VIEW pairs).
--
-- One row per real Snowflake object we know about, whether or not it has
-- a Wimbi-side view yet. Source of truth: analytics_mirror/models.py's
-- own docstrings (each one already says "Mirrors V_X" - this just
-- consolidates that into one queryable, browsable place) plus the actual
-- synced table list in analytics_mirror_raw as of 2026-09-09.
--
-- Safe to re-run: drops and rebuilds from scratch. This is a hand-curated
-- reference table, not live data - update the INSERTs below when the
-- mapping changes (a table gets modeled, a rename happens), then re-run.

DROP TABLE IF EXISTS public.wimbi_analytics_mapping;

CREATE TABLE public.wimbi_analytics_mapping (
    table_id            SERIAL PRIMARY KEY,
    description         TEXT NOT NULL,
    wimbi_name          TEXT,       -- analytics_mirror.<name>; NULL if not yet modeled in Django
    analytics_db_name   TEXT NOT NULL, -- the Snowflake/raw object this mirrors
    is_similar          BOOLEAN,    -- true = same name (case/prefix aside); false = deliberately renamed; NULL = not yet modeled, N/A
    is_normalized       BOOLEAN,    -- true = a real VALUE transform happens (not just renaming), e.g. country name -> ISO-2
    normalization_notes TEXT        -- what/how, or any other caveat worth flagging (surrogate ids, type-precision risk, etc.)
);

INSERT INTO public.wimbi_analytics_mapping
  (description, wimbi_name, analytics_db_name, is_similar, is_normalized, normalization_notes)
VALUES

-- Dimension tables: real integer PKs, straight rename, no value transforms.
('Country reference (ISO code, currency, cross-system ids)', 'dim_country', 'DIM_COUNTRY', true, false, NULL),
('Market/Client Feature categories (7 flags referenced by DimProgram)', 'dim_mcf', 'DIM_MCF', true, false, NULL),
('Every real country+program combination (29 rows)', 'dim_program', 'DIM_PROGRAM', true, false, NULL),
('Per-country season definitions with real date ranges (171 rows)', 'dim_season', 'DIM_SEASON', true, false, NULL),
('Every source system feeding each country+program (218 rows)', 'dim_system', 'DIM_SYSTEM', true, false, NULL),

-- Tables with a real natural key, name matches or near-matches Snowflake.
('Cross-system client identity links feeding gl_client_id resolution', 'bridge_client_source_ids', 'BRIDGE_CLIENT_SOURCE_IDS', true, true,
  'source_country_code normalized from SOURCE_COUNTRY (full name, e.g. "Malawi") via analytics_mirror.to_iso_country() - replicates analytics_mirror/country_codes.py by hand, kept in sync manually, see that function''s own comment.'),
('One row per farmer - reach/activity summary feeding the farmer profile page', 'v_client_reach', 'V_CLIENT_REACH', true, true,
  'country_code normalized from COUNTRY (full name) via to_iso_country(). No phone number column exists at this layer - search-by-phone is not backed by real data here.'),
('Field officer performance rollup (560 rows, pre-aggregated)', 'fo_performance', 'V_FO_PERFORMANCE', true, false,
  'FO_ID is blank even when FO_KEY/FO_NAME are populated - do not rely on it. Loan/sale aggregates are null (not 0) when an FO has no clients of that kind.'),

-- Tables with no reliable natural key - Wimbi side uses a ROW_NUMBER()
-- surrogate id in the view, not a stored value. Verified safe for
-- current usage (2026-09-09): see analytics_mirror_views.sql's own note.
('Per-farmer timeline events: Sale / Loan Disbursed / Buyback', 'v_client_journey', 'V_CLIENT_JOURNEY', true, true,
  'country_code normalized from COUNTRY via to_iso_country(). id is a ROW_NUMBER() surrogate (no natural key) - safe for current per-farmer, single-request usage; re-check if this table is ever paginated across requests.'),
('Sale line items (one row per product on an order) - line grain, not client grain', 'sales_line', 'V_SALES_DETAIL', false, true,
  'Deliberately renamed from V_SALES_DETAIL to reflect line-item grain. country_code normalized via to_iso_country(). id is a ROW_NUMBER() surrogate. LATITUDE/LONGITUDE synced as bigint upstream - real GPS decimals may be truncated; verify against real values before trusting map display.'),
('Loan portfolio, one row per loan (not per client)', 'loan_portfolio', 'V_LOAN_PORTFOLIO', true, false,
  'country kept as the raw full name (e.g. "Malawi"), NOT normalized - deliberate, per the model''s own docstring: normalize at the point RBAC/scoping actually uses it, not here. id is a ROW_NUMBER() surrogate - no natural key looked reliable in real sample data.'),
('Pre-aggregated program summary, one row per (year_month, country, program)', 'program_summary', 'V_PROGRAM_SUMMARY', true, false,
  'country kept as raw full name, not normalized - consumed as-is per ADR-007 rather than re-derived. id is a ROW_NUMBER() surrogate over the natural (year_month, country, program) composite, which should make it stable in practice as long as that combination stays unique per row.'),
('Repayment transactions (largest real table, ~4.3M rows)', 'repayment_transaction', 'V_REPAYMENT_ANALYSIS', false, false,
  'Deliberately renamed from V_REPAYMENT_ANALYSIS - transaction grain, not "analysis". country kept as raw full name, not normalized. id is a ROW_NUMBER() surrogate. REPAYMENT_PHONE is a real column here even though v_client_reach has no phone column at all.'),

-- Modeled in Django, but no raw table has been synced via this Airbyte
-- connection yet - nothing to build a view over.
('SuccessFactors employee extract - role/department mapping for RBAC (deferred)', 'sf_employees', 'SF_EMPLOYEES (SuccessFactors, not yet connected via this Airbyte source)', NULL, NULL,
  'Model exists in analytics_mirror/models.py with the same country_code normalization pattern (handles non-standard values like "RW-TBR", "ETH"). No analytics_mirror_raw table exists yet, so no view has been built.'),

-- Synced by Airbyte, but no Django model reads them yet - these map to
-- the bulk-uploader glossary's Client/Location/Product/People entities
-- (_docs/bulk-uploader.md). Real, future work - not building views for
-- tables nothing reads yet.
('Client dimension - candidate for the bulk-uploader Client entity', NULL, 'DIM_CLIENT', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('Date dimension', NULL, 'DIM_DATE', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('Exchange rate reference', NULL, 'DIM_EXCHANGE_RATE', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('Location dimension - candidate for the bulk-uploader Location entity', NULL, 'DIM_LOCATION', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('People/staff dimension - candidate for the bulk-uploader People entity', NULL, 'DIM_PEOPLE', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('Product dimension - candidate for the bulk-uploader Product entity', NULL, 'DIM_PRODUCT', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet.'),
('Raw client listing - candidate for the bulk-uploader Client entity', NULL, 'V_CLIENTS', NULL, NULL, 'Synced into analytics_mirror_raw; no analytics_mirror view or Django model yet. Possibly overlaps DIM_CLIENT - worth checking which is the better source before modeling either.');

-- Quick browse:
SELECT table_id, description, wimbi_name, analytics_db_name, is_similar, is_normalized
FROM public.wimbi_analytics_mapping
ORDER BY table_id;
