# Railway migration: preserve established runtime credentials

25 October 2026. This source correction is required before the next matched
API/worker deployment. It does not apply a migration, change hosted credentials,
replay MFA recovery or grant new account access.

## Observed defect and resulting behavior

The ordinary `migrate` entrypoint previously issued `ALTER ROLE ... PASSWORD`
for an existing `taximobile_runtime` role before Alembic. That changed its stored
SCRAM verifier even when the supplied password matched; a mismatched deployment
secret could also replace the established login rather than fail visibly.
Credential recovery is already complete and must not run again during rollout.

The migrator now verifies that its runtime URL targets the same isolated staging
host, port and database, uses the dedicated runtime identity and matches its
configured password. It rejects URL transport overrides before opening the owner
connection. Under the existing deployment advisory lock, an established role must
authenticate through the configured database transport and pass the existing
least-privilege/TLS checks in a read-only transaction. Connection, statement and
lock timeouts bound this preflight. Failure stops before Alembic, table grants,
projection refresh, seed or recovery; errors omit credentials and driver details.

An existing role receives no password or role-attribute alteration. The absent-role
path retains initial creation for a separately authorized first environment setup.
After a successful migration, the existing missing-table/sequence grant and
analytics verification protocol still applies. That protocol is not expanded by
this fix. No schema, dependency, UI or product-policy change is required.

## Evidence and next gate

The [verification record](runtime-preservation-verification-20261025.json) retains
the failing regression and intermediate test failure alongside **71 passing focused
tests** and **1,158 passing unit tests**, with zero final failures/errors/skips.
One existing Starlette/httpx deprecation warning remains; no dependency was changed
to suppress it.

A fresh owned PostgreSQL 16.14 loopback cluster exercised actual SCRAM authentication:
first role creation, two subsequent successful logins preserving the exact stored
verifier and checked role attributes, rejected wrong password, and rejection of
deliberately elevated role/schema privileges without silently repairing them.
The successful preflight sessions were read-only with five-second statement and
two-second lock timeouts. Its synthetic credentials are protected locally; neither
passwords nor password verifiers enter the evidence. The cluster is stopped.
Retained restore/membership fixtures and Railway were not mutated.

The successor subsequently passes [terminal CI 238](runtime-preservation-ci-terminal-20261026.json):
all eight required jobs and **1,458 backend cases**, with zero failures/errors/skips,
including all 15 new preservation cases and eight real TLS probes with cleanup.
The tested merge and branch head have the same immutable tree. Android/web,
unsigned iOS simulator verification, audits and blocking image checks pass.
[CI 236](document-s3-ci-terminal-20261025.json) remains its predecessor's evidence.
The [25 October hosted read](staging-tls-server-preflight-20261025.json)
still observes schema 0052, SSL off and five plaintext TCP clients. Apply the
[guarded TLS/migration packet](staging-tls-rollout.md) only after its target,
capacity, protected rollback and matched-source prerequisites hold. Hosted
document ingestion, official scanner capacity, real devices and public launch
remain separately unaccepted.

Subsequent [local 0054 restore verification](staging-restore-schema54-r2-20261025.json)
also exercises this successor's existing-role preflight and unchanged grant
protocol against restored application state. Three imported views initially had
the local restore administrator as owner; the failed observation is retained and
only that new local target's ownership was corrected before continuation. A
fresh hosted ownership read confirms those views already belong to the expected
migration owner. This fixture correction does not authorize a hosted role/grant
expansion or establish a hosted upgrade. Native CI is now accepted separately;
the [26 October capacity stop](staging-capacity-stop-20261026.json) prevents the
prepared hosting apply under the existing Trial-only boundary.
