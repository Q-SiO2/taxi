# Staging database TLS rollout packet

Prepared 24 October 2026. Status: **PREPARED, NOT APPLIED**. Implements the
[transport contract](database-tls.md) within the existing synthetic alpha.
[CI 230](database-tls-ci-observation-20261024.json) for source
`3698f60334721d3289d616bb598ffee36cb81b24` passes all eight real TLS probes but
fails four API test fakes. The local correction passes 44 system API tests;
fresh complete successor CI is required.
No certificate, server/consumer setting, HBA rule or deployment has been changed
by this packet. Do not reuse the localhost test certificate for this target.

## Exact boundary

| Resource | Bound target |
| --- | --- |
| Railway project | `9f841575-c4f3-4a4d-bb83-2e6ff92e436e` |
| Staging environment | `ed891bc6-51ff-4acc-aed3-bb536931b855` |
| Database service | `41ccd6b2-41e2-4886-8d96-cc56f62aaab7` / `alpha-postgis` |
| Database identity | `alpha-postgis.railway.internal` / `taximobile_alpha_ed891bc651ff` |
| API service | `758fa7d5-f8b8-4730-a00f-438e28184e35` |
| Worker service | `eb42d0ba-feae-4f7a-9c86-48f4d38006d0` |
| Existing active volume | `8ed86e48-25f5-4fa6-8feb-2f930ba8b547`, 500 MB |
| Preserved detached volume | `b9097b45-80a9-4964-9844-c247b08d1db5`, never delete |

These identities are guards, not secrets. Re-read deployment identity, source
digest, running command, PG data/config/HBA paths, current SSL settings, HBA rule
order, ownership, capacity and active connections before mutation. An unexpected
target, concurrent deployment or changed baseline invalidates this preparation.
Do not copy connection credentials or HBA address details into public evidence.

## Preparation before applying

1. Require the exact candidate's required CI jobs and retained TLS/JUnit evidence
   to pass. Keep the failed local observer records. Bind matched API/worker images
   to the accepted commit, migration 0053 and deployment configuration.
2. Verify current Trial availability/capacity without upgrading the plan, adding
   a resource or deleting either volume. A usage total alone is insufficient
   evidence of the plan or remaining credit. Stop dependent hosting changes if
   current authorized capacity cannot be established; continue independent work.
3. Retain the [protected database snapshot and qualified restore](staging-upgrade.md).
   Review whether source changes since capture require a new distinct rollback
   capture. Never overwrite or replay the original archive merely for a green
   observer. Capture the current server/configuration rollback separately through
   the protected boundary; a database dump does not contain TLS private keys.
4. Provision a distinct staging server key/certificate with SAN
   `alpha-postgis.railway.internal`, server-auth usage and a valid trust chain.
   Use the deployment trust/key boundary; CA private signing authority does not
   belong in the API, worker, Git, CI artifacts, variables printed in logs or the
   public evidence packet. Record issuer, public fingerprint, expiry and renewal
   responsibility. Independent custody/expiry monitoring remains a production gate.
5. Store server files in a dedicated persistent subdirectory of the confirmed
   active PG data volume, protected by postgres ownership, directory mode 0700
   and private-key mode 0600. Refuse symlinks or existing files; write atomically
   under a distinct versioned name. Preserve prior versions for rollback. Back up
   key material only encrypted, with custody and recovery verification. Do not
   combine it with application JWT/MFA/document keys.
6. Prepare one public CA trust bundle for every consumer and a policy-capable
   rollback image. Railway's PEM input avoids an unmounted file path. Pin the
   public CA fingerprint in the bounded record; never output private keys or DSNs.
   Default system trust is valid only for an actually trusted issuer/hostname.

## Ordered apply and stop points

1. Validate server key/certificate match, SAN/validity/chain, file ownership and
   reload capability. Apply persistent `ssl=on`, certificate/key paths and TLS 1.2
   minimum through the confirmed PostgreSQL configuration. Preserve the original
   values. Inspect PostgreSQL file-setting/reload errors and a new actual TLS
   handshake before changing consumers. Keep the local Unix-socket recovery path.
2. Configure matched API, worker and pre-deploy migrator with
   `TAXIMOBILE_DATABASE_TLS_MODE=verify-full` and exactly one correct CA source.
   Remove URL SSL/host overrides. No runtime role elevation or credential/MFA
   recovery is needed for TLS; never run bootstrap/seed as a transport repair.
   Use deliberate migration authority only if applying 0053 from the accepted
   source; check its separately rehearsed constraint and grant protocol.
3. Verify actual API readiness, restricted runtime role/schema and encrypted
   connection; verify worker health/loops and API LISTEN registration. Reconnect
   each consumer so an old plaintext pooled session cannot masquerade as proof.
   Observe current client sessions server-side without exposing participant data.
4. Use bounded **read-only** handshake probes from the actual deployment boundary:
   valid trust succeeds; unrelated CA and wrong hostname produce certificate
   rejection. No applicant, roster, recovery, trip or money command is necessary.
5. Only after all consumers work, reject remote non-TLS client connections using
   deliberately ordered HBA rules covering the applicable IPv4/IPv6/private
   addresses and replication paths. Preserve existing authenticated local recovery
   and the intended user/database admission restrictions; do not insert a broad
   trust rule. Validate parsed HBA rules and reload errors. Open fresh TLS and
   explicit non-TLS connections: the former must work, the latter must fail.
6. Restart/redeploy from the persisted configuration deliberately and recheck
   identity, TLS, readiness and worker/listener behavior. Verify equivalent
   `verify-full`/CA handling for remote libpq backup/maintenance consumers; an
   encrypted SSH/local-socket backup is a distinct transport path. Record actual
   source/digests, schema, public certificate fingerprints/expiry, checks, failure
   observations and final disposition, with no secret or participant contents.

Stop on any unmet guard or failed check. Preserve the actual failed result and
repair its cause. Configuration strings, a successful TCP connection, `ssl=require`
or an image build are insufficient acceptance. Do not accept production from
this synthetic staging exercise.

## Rollback without downgrading the boundary

Before rejecting plaintext, consumer rollback must still use the accepted CA and
verified transport, on a policy-capable image. After HBA enforcement, a broken
certificate/consumer requires repairing the chain, hostname, protected paths or
matched configuration; do not relax verification to restore apparent readiness.
Retain an existing valid certificate/trust overlap for a coordinated rollback.
If no verified configuration can serve, keep traffic unavailable and preserve
data/local authenticated recovery rather than accepting unverified sessions.

Migration and membership rollback obey the separate
[policy boundary](staging-upgrade.md#membership-aware-rollback-boundary): no old
build may take new member-only work while ignoring the requirement. Never drop
0053 or silently turn the policy off as a TLS repair. The old synthetic alpha is
not a public service acceptance or an accepted member-only fallback.
