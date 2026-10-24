# Verified PostgreSQL transport — 24 October 2026

Status: **source and local PostgreSQL checks pass; new full CI and hosted TLS open**.
This R3 packet follows the [backup/restore rehearsal](staging-upgrade.md). The
live alpha's database connection was observed unencrypted; source implementation
does not change that state or accept a real-world launch.

## Connection contract

One immutable `DatabaseTLS` policy covers SQLAlchemy API/worker sessions, the
dedicated asyncpg LISTEN connection, Alembic, Railway's guard/provision/verification
connections, demo preparation and selective outbox operations. No new dependency.

- `TAXIMOBILE_DATABASE_TLS_MODE` accepts only `disable` or `verify-full`.
  Production defaults to and requires `verify-full`. Development/test and the
  existing staging alpha default to `disable` until deliberately configured;
  this preserves the alpha but is not staging TLS acceptance.
- `verify-full` uses a client SSL context with required CA validation, hostname
  checks and TLS 1.2 minimum. It cannot fall back to plaintext or weaker trust.
  Default system roots apply unless an operator supplies a custom CA.
- Custom trust uses exactly one of `TAXIMOBILE_DATABASE_CA_FILE` (an absolute,
  readable PEM bundle path) or `TAXIMOBILE_DATABASE_CA_PEM` (PEM bundle text).
  Railway can use the PEM environment input without placing certificates in Git;
  file-based deployments must mount the bundle into every applicable process.
  These are CA certificates, never server private keys. A CA cannot be supplied
  while the policy disables TLS. Malformed/unreadable trust fails explicitly.
- Database URL SSL/host override query options are rejected, including `ssl`,
  `sslmode`, `sslrootcert`, `direct_tls`, `host` and service-file overrides. Remove
  those URL options when adopting the explicit policy. This prevents different
  URL parsing by SQLAlchemy and direct asyncpg from weakening verification.
  Verified connections require an explicit TCP hostname; Unix sockets do not
  establish TLS identity.

Settings capture the policy at startup. Restart consumers with a reviewed new CA
bundle when rotating trust; first overlap valid CAs where appropriate. Native
libpq backup clients use the equivalent `PGSSLMODE=verify-full` and an explicit
`PGSSLROOTCERT` PEM file. Never set `require` as a substitute for identity checks.
The existing socket-based staging backup uses encrypted SSH transport separately.

## Local verification and CI boundary

The [terminal local record](database-tls-local-verification-r5-20261024.json)
reports **8 passed, zero failures/errors/skips** against real authenticated local
PostgreSQL. ORM sessions exercise both file and PEM trust; unrelated CA, wrong
hostname and a separate plaintext server are rejected. The live-event listener
registers over TLS and an actual certificate-verification failure leaves it
unready. An already-current Alembic migration succeeds with valid trust and
fails with the unrelated CA. No business command is replayed by those probes.

The normal restricted-runtime verification also observes **TLS 1.3** with
`verify-full`, schema **0053**, 81 public tables, no runtime administrative or
public-schema CREATE authority, and a successful analytics-projection refresh.
Both local clusters are stopped and retained. This exercises the qualified
Windows restore target, not Railway or a production certificate.

Earlier [r3](database-tls-local-verification-r3-20261024.json) and
[r4](database-tls-local-verification-r4-20261024.json) each retain one failed
listener assertion: the probe could not observe the expected application log.
The final probe observes the real driver's handshake instead; it still requires
the certificate exception and unready state. Earlier timed-unready-only checks
were insufficient evidence of the rejection cause and are superseded.

The [source verification](database-tls-source-verification-20261024.json) binds
the final **1,036 unit tests**, **279 infrastructure tests**, source hashes and
contract/configuration checks. These counts do not represent a new full backend
or hosted acceptance result. The predecessor's green CI belongs to its own SHA.

The CI wrapper runs the **entire backend suite without a selector**, with eight
real TLS probes included and no skips permitted. It generates short-lived test
PKI inside an explicitly guarded disposable GitHub/PostGIS service, verifies
valid/invalid trust and a separate plaintext service, then restores the original
server configuration and removes its generated server key/certificate. The full
JUnit and bounded TLS report are retained and bound to candidate evidence.
No Docker engine was available for this wrapper locally: its first execution
must be accepted from fresh exact-source CI before hosted rollout.

## Deployment sequence and acceptance

First test the complete policy against local PostgreSQL: valid CA/hostname,
untrusted CA, wrong hostname, absent server TLS, SQLAlchemy/asyncpg listener and
migration paths. Keep actual server-side TLS observations and failed handshakes;
configuration strings alone are insufficient evidence.

Then prepare the staging server certificate/key and trust bundle through protected
deployment boundaries. Enable server TLS, configure/replace all consumers with
full verification, inspect encrypted sessions and health/readiness, and reject
remaining remote non-TLS connections only after consumers are ready. Keep local
backup/migration recovery and a coordinated rollback that preserves verification.
No paid resource, role/credential recovery, volume deletion or public activation
is authorized by this source packet. Current funding and all existing R1 gates
remain prerequisites for their dependent hosting/production actions.
