# Union membership admission — 23 October 2026

Status: **backend implementation and isolated verification; deployment and
operational acceptance pending**. This is an R5/R8 slice of the
[real-world launch goal](../real-world-launch.md), not closure of that goal.

## Owner decision and implementation

The first city is Fès, the operator is the transport union, drivers must be union
members, and passengers register normally. The owner explicitly selected the
existing cooperative register for union membership. Reuse `Cooperative` and
`CooperativeMembership`, linked by `Operator.cooperative_id`; do not create a
second member register or infer the union's legal form from the software enum.

Migration `20261023_0053` adds `Operator.requires_active_membership`, default false,
and a database constraint requiring a linked register when true. Existing open
operators remain open. **The Fès union operator must enable this policy before
admitting its drivers**; the default is not a deployment configuration approval.
No Fès configuration or real roster has been provisioned by this packet.

For a closed-shop operator, the backend requires an ACTIVE organization and ACTIVE
membership in that exact register. A future `joined_at` or expired `ended_at`
fails admission; null legacy dates are accepted with ACTIVE status. Professional,
vehicle, global account and city/service eligibility remain independent checks.
Driver approval, a self-entered number and a client claim cannot enroll a member.

The guards cover going online, on-demand/fixed-route candidate discovery and
final offer allocation, immediate acceptance, scheduled-offer discovery,
scheduled commitment and live handoff. Candidate filtering precedes selection
limits. Final admission refreshes authority and holds PostgreSQL shared locks on
the policy, member and organization rows through the transaction. An ordinary
membership/policy update either commits first and is observed, or waits for the
already admitted command. Production acceptance evaluates membership time after
lock waits; explicitly supplied simulation clocks remain deterministic.

Passenger registration is unchanged. Withdrawal does not block an already
accepted trip's progress/completion, payment, support, safety or history. Existing
global-account and professional restrictions retain their own rules. Scheduled
handoff rechecks membership: a prior commitment is not permission to create a new
live assignment after withdrawal.

The existing scoped operator API exposes the policy. Updates retain
`MANAGE_OPERATORS`, scope checks, recent MFA, row locking and audit. The Boolean
does not grant staff access or enroll anyone. Staff register-maintenance tools,
policy controls and localized actionable driver explanations are still needed
for an operable capability.

## Verification and evidence boundaries

The [verification record](union-membership-verification-20261023.json) retains
source digests, exact reports and failed observations. Tests use a fresh owned
loopback PostGIS cluster and per-test cloned databases with synthetic accounts.
They do not use the union roster, staging credentials or Railway data.

- The migration upgraded to 0053, downgraded to 0052 and re-upgraded successfully.
- All 25 focused cases pass: membership states/date boundaries/register scope,
  SQL predicates, both immediate service types, HTTP availability/passenger
  registration, revocation and policy activation after offering, observed
  withdrawal/acceptance lock races in both orders, accepted-trip completion with
  a server-quoted payment, scheduled discovery/commitment/handoff and the raw
  database constraint.
- Unit checks pass across split runs: 986 tests plus the three OpenAPI tests.
  The first broad run and isolated retry hit the original 45-second schema-worker
  timeout. A measured Windows export took 114 seconds under concurrent test
  load; the worker now has a finite 180-second budget. Isolation, exact schema
  comparison, credential exclusion and network-denial assertions are retained.
- All **38 existing integration regressions** pass across the 12-case immediate
  authorization file and the 26-case city HTTP, scheduled acceptance/live
  protection and passenger/driver/payment lifecycle run. Mobile contracts
  (84 HTTP plus one WebSocket), web contracts (112 HTTP), expanded source
  credential checks, compilation and documentation checks also pass.
  Counts and outcomes belong to their exact reports. The first dispatch
  regression missed the five-second lock observation under load; its unchanged
  12-case file subsequently passed in isolation. The failed run is retained and
  the lock-observation requirement was not weakened.

These are local source/synthetic results. The preceding
[7d candidate's CI](r2-ci-terminal-20261023.json) passed backend, Android, web and
unsigned iOS verification, with dependency review cancelled. That earlier commit
does not include this feature. A successor must receive its own immutable CI;
dependency comparison, independent review and release acceptance remain open.

## Controlled rollout and next work

1. Freeze/review the successor source and verify full CI, contracts and migration
   evidence. Preserve failures and keep the existing draft PR unmerged until its
   actual gates are accepted.
2. Implement scoped, audited register administration and operations policy UX
   against existing permissions; do not expand real staff grants. Verify member
   suspension/end, effective dates, unauthorized access and participant-facing
   EN/FR/AR behavior across the four supported styles.
3. Before a deliberate staging rollout, bind API and worker images to the same
   reviewed migration/contract, preserve backup/rollback data and prove the
   staging upgrade/recovery path. Existing deployed schema remains 0052.
4. After a closed-shop policy is enabled, an older API that lacks these checks is
   **not a safe admission rollback**. Pause affected admissions through existing
   controls before any incompatible rollback/downgrade, preserve active trips,
   and restore a version that enforces the membership policy. The isolated
   downgrade test does not authorize removal of a live access rule.
5. Obtain exact operator identity, authorization, verified roster ownership,
   service boundary and the remaining [R1 operating decisions](r1-decisions.md)
   before real participant enrollment or transport activation. Keep Trial-only
   spending and protected staging volumes unchanged.

No hosted migration, membership enrollment, privilege expansion, native rebuild,
physical-device acceptance or real-world activation is claimed here.
