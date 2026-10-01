# Intake table hardening — applied 2026-10-01

Project: `iunbpyiylsbkscjaisid` (Intake). Scope: the 21 public tables other than `entries`, their two sequences, and four legacy functions.

## Applied

- Revoked all table and column privileges from PUBLIC, anon and authenticated on the 21 legacy tables, including TRUNCATE and MAINTAIN.
- Enabled RLS on seven previously unprotected tables: admin_audit_log, connector_installations, connector_principal_bindings, connector_provisioning_audit_log, intake_migration_runs, tenant_api_keys and tenants.
- Added command-specific policies preserving existing dedicated backend role access. These management-table policies preserve previous backend access; they do not add tenant isolation.
- Restricted entity_catalog_watermarks' existing policy to intake_runtime. Other existing tenant policies retained.
- Removed public client execution of four legacy functions. Preserved previously effective backend trigger-function execution through explicit grants.
- Removed anonymous/authenticated sequence privileges and postgres-owned public table/sequence defaults.
- Preserved service_role privileges, backend role membership, Pit table policies/grants and both Pit reader functions.

## Verified live

- All 22 public tables have RLS enabled.
- All 21 legacy tables deny anonymous/authenticated table and column privileges; the transaction asserted these and unchanged backend table privileges before commit.
- Before/after catalog comparisons confirmed unchanged dedicated backend table and function rights, existing tenant policies, and Pit permissions.
- All 42 read-only Data API probes (21 tables × anon/authenticated, limit=0) were denied with HTTP 401/403. No legacy table records were fetched.
- Pit search and bounded range reads succeeded after deployment.

## Boundary

The database account cannot alter defaults owned by Supabase's platform role `supabase_admin` (membership check is false). Those defaults still auto-grant client table/sequence privileges for objects created by that role. Existing tables are hardened; future migrations should create objects as postgres and explicitly review grants/RLS. Future function defaults were outside this table-hardening change and still need explicit privileges when authoring functions.

This verifies permissions and Pit retrieval, not the running Intake application's end-to-end journeys. Service-role access remains privileged by design.

## Recovery

Applied SQL: [legacy-table-hardening.sql](legacy-table-hardening.sql).
Exact prior-grant rollback: [legacy-table-hardening.rollback.sql](legacy-table-hardening.rollback.sql). Rollback intentionally restores prior exposure; use only after reviewing the reason.

Private metadata snapshots and API probe results: `~/.local/share/the-pit/evidence/table-hardening/` (no table records or credentials). No data was changed.
