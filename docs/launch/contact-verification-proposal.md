# GAP-020 contact verification proposal

Prepared 3 November 2026 for the Fès real-world launch. Status: **PROPOSAL —
not approved for schema/API implementation or provider activation**. This packet
turns the owner's selection of both email and SMS into a bounded contract for
review. It does not select a vendor, establish a budget, change staff identity
controls or approve sending messages to real contacts.

## Decisions and open items

| Topic | Status |
| --- | --- |
| Required contact channels | **Decided:** both email and SMS are required (R1 D07). |
| Verification purpose | Proposed: prove current control of each submitted address and number before either is labelled verified. |
| Delivery provider and account owner | Open; must be named before credentials or live delivery. |
| Budget ceiling and payer | Open; no spending is authorized by this proposal. |
| Contact normalization and change proofing | Open for product/security review. |
| Challenge TTL, attempt, resend and daily limits | Proposed defaults below; security/identity owner must approve before implementation. |
| Recovery eligibility using a verified channel | Open; do not replace offline recovery or staff MFA by inference. |
| Staff identity | Separate from passenger/driver contact verification; retain existing operations MFA and recovery controls. |

## Proposed user and backend contract

1. Registration may collect email and mobile number, but each remains explicitly
   `PENDING` until independently verified. The account cannot represent one
   channel as verified because the other succeeded.
2. An authenticated passenger or driver can request verification for one of
   their own pending channels. Replacing a contact requires recent
   re-authentication; the account displays that the replacement is pending.
   Whether the old verified contact remains usable during this period needs
   security-owner approval.
3. The API accepts the request without revealing whether a destination belongs
   to another account. It returns the same public shape for queued, throttled,
   unavailable and ineligible delivery, with a correlation-safe request ID only
   if that ID reveals no contact or account data.
4. A successful delivery request creates a purpose-bound, expiring challenge.
   A valid challenge is redeemed once, under a row lock, and only for its
   original user, channel and exact pending contact. Redemption marks only that
   channel verified and records a timestamp. Replays, expired codes, wrong
   codes, contact changes and concurrent attempts fail without changing account
   state.
5. Delivery uses an adapter behind a durable outbox so a worker outage cannot
   lose a committed challenge or report false verification. Retries are
   idempotent and bounded; exhausted delivery leaves the channel pending and
   visible as needing retry. Synthetic adapters are used in local/CI tests.
6. Password reset through email/SMS is not added until a separate decision
   defines recovery eligibility, account enumeration behavior, session
   revocation, high-assurance driver handling, and compromised-account support.
   Existing offline recovery codes continue to work under their current policy.

## Proposed security and privacy defaults for review

- Generate a cryptographically random eight-digit code; store only a
  purpose-bound keyed digest, with the key held in the runtime secret store.
- Expire challenges after ten minutes; permit five verification attempts; apply
  a sixty-second resend cooldown and finite account, normalized-contact, IP and
  aggregate limits. Parameterize the limits and verify atomic enforcement
  across concurrent API workers before accepting them.
- Invalidate older challenges for the same user/channel when a new challenge is
  issued. Do not let a code verify an address or number different from the
  challenge destination snapshot.
- Keep code, message body, contact value, provider credentials and provider
  response bodies out of logs, metrics, analytics and ordinary audit fields.
  Persist only what is necessary for delivery, abuse control, status and
  retention; set a short cleanup window for consumed/expired challenges.
- Use generic request responses and rate-limit keys derived from a keyed digest
  of normalized identifiers. Avoid sending verification messages merely to
  disclose whether an account or contact exists.
- Require TLS delivery endpoints and provider-side account protections;
  verify callback authentication and replay handling if callbacks are used.
  No unauthenticated provider webhook may mark a channel verified.
- Keep email and phone delivery independently observable. A provider outage on
  one channel must not block verification of the other, and must never satisfy
  the missing channel's requirement.

## Bounded implementation sequence after policy approval

1. Approve normalization, pending-contact replacement behavior, limits,
   retention, recovery boundary and accountable provider/budget owners.
2. Add database state and a forward-only migration with uniqueness/concurrency
   behavior documented in `docs/database.md`; preserve existing account and
   recovery records. Do not backfill unverified legacy contacts as verified.
3. Implement provider-neutral challenge creation/redemption, outbox delivery
   contract, generic responses, hashed rate limits and redacted fixed-field
   audit events in the auth domain.
4. Add localized passenger/driver flows in EN/FR/AR with pending, sent,
   cooldown, invalid, expired, verified and provider-unavailable states. Do not
   render a verified badge before the backend confirms redemption.
5. Verify uniqueness races, cross-account and cross-purpose replay, expiry,
   attempt exhaustion, resends, contact replacement, enumeration, throttling,
   provider outage/retry, logging redaction and session behavior.
6. Select and configure real providers only after the owner identifies the
   account holders, budget and credential custody. Verify delivery using
   authorized test destinations, then run production-like abuse/outage drills.
7. Close GAP-020 only after device acceptance, independently reviewed policy,
   provider evidence and approved recovery/support operations. Source tests or
   synthetic adapters alone do not close the gap.

## Required approvers and evidence

The owner names the email and SMS account/budget holders and spending ceilings.
The security/identity lead approves challenge parameters, contact replacement,
enumeration and recovery boundaries. The privacy/legal lead reviews purpose,
retention and data handling. The release/on-call owner records provider
availability and escalation. Required evidence includes the approved policy
revision, schema/API review, candidate-bound tests, redaction inspection,
provider configuration provenance, delivery/outage rehearsal and Android
device acceptance. Keep real contact details and credentials out of this
repository.
