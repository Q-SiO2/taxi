# TaxiMobile — Threat Model and Security Verification Matrix

## Current standing — 2026-09-03

This is the repository threat-model baseline for the current modular-monolith,
mobile, web, worker, PostGIS, and provider architecture. It is **not an accepted
independent security assessment**. It turns known security assumptions into
reviewable threats and tests. An independent reviewer must validate it against an
immutable release, deployed staging, provider configuration, and real operating
procedures before any public launch.

The deployment decision remains **not ready for a public or live city pilot**.
Open remediation and evidence are tracked in [`gaps.md`](gaps.md); promotion and
participant safeguards are defined in [`testing.md`](testing.md).

## 1. Scope

### Included

* Passenger and driver Android/iOS clients.
* Public applicant and protected operations web applications.
* FastAPI public API and private worker process.
* PostgreSQL/PostGIS, migrations, backups, analytics and audit records.
* Driver-document object storage and malware scanning boundary.
* MapLibre style/tile delivery and Valhalla/GraphHopper routing.
* WebSocket, PostgreSQL live-event transport and FCM/APNs delivery.
* Cash, manual bank/M-Wallet transfer claims, refunds and reconciliation.
* Support, safety, paging, retention and legal-hold operations.
* Build, CI, artifact, container, deployment and staff-access boundaries.

### Excluded or deferred

* CMI/card processing and any unimplemented provider protocol.
* Direct emergency-services dispatch.
* Unapproved passenger-driver calling or masked-number service.
* A specific production cloud, DNS, registry, secret manager or data region.

An excluded feature must remain unavailable; exclusion is not permission to ship
an unreviewed substitute.

## 2. Security objectives

| ID | Objective |
| --- | --- |
| SO-01 | Only the authenticated participant can read or command their account, application, ride, payment, notification, support or safety resources. |
| SO-02 | Driver, vehicle, city and service eligibility are backend-authoritative and cannot be granted by client state. |
| SO-03 | Staff authority is operations-audience, permission- and scope-bound, recently MFA-verified where required, and auditable. |
| SO-04 | One city/operator cannot read, count, mutate or infer another scope's restricted records. |
| SO-05 | Assignment, fare, payment, earning, refund and configuration history cannot be silently rewritten or replayed. |
| SO-06 | Location, identity documents, case narratives, contact data and credentials are minimized and never exposed through logs, metrics, events or broad APIs. |
| SO-07 | Failure of database, routing, push, scanner, pager, storage or worker dependencies fails safely and is observable. |
| SO-08 | Released source, schema, dependencies, images and client artifacts are traceable to one reviewed immutable commit. |
| SO-09 | Destructive account/data/rollout actions require explicit authority, bounded reasons, recoverability rules and independent review where policy requires. |
| SO-10 | A compromised client, provider callback, staff browser or ordinary administrator cannot become backend or nationwide authority. |

## 3. Assets and impact

| Asset | Confidentiality | Integrity | Availability/safety impact |
| --- | --- | --- | --- |
| Password hashes, access/refresh tokens, MFA seeds/recovery codes, CSRF values | Critical | Critical | Account takeover and staff compromise |
| Driver identity and vehicle documents | Critical | High | Privacy harm, fraud, unlawful recruitment |
| Current and historical location | Critical | High | Stalking, physical safety, wrong dispatch |
| Ride participant/assignment state | High | Critical | Wrong pickup, impersonation, physical harm |
| Tariffs, quotes, fares, payments, earnings and refunds | High | Critical | Customer/operator/driver money loss |
| Support/safety narratives and assignments | Critical | Critical | Victim exposure, missed urgent response |
| City/operator configuration and rollout state | Medium | Critical | Illegal/unsafe service activation |
| Audit, analytics, readiness and retention evidence | Medium | Critical | Undetected abuse or false launch decision |
| Signing keys, CI tokens, image registry and deployment secrets | Critical | Critical | Supply-chain or environment takeover |
| Service availability, route graph, notifications and worker leases | Medium | High | Stranding, stale decisions, missed offers/pages |

## 4. Trust boundaries

| ID | Boundary | Untrusted side | Trusted/authoritative side | Required control |
| --- | --- | --- | --- | --- |
| TB-01 | Mobile/web to public API | Device, browser, network and all client state | TLS ingress and backend authorization | Exact host/origin, HTTPS, schema validation, authenticated ownership, rate limits |
| TB-02 | Operations browser to operations API | Browser storage, extensions, CSRF origin, stolen mobile token | Operations audience/session and scoped grants | Secure cookie, CSRF, MFA, permission and scope checks, no mobile-token substitution |
| TB-03 | API/worker to PostGIS | Query inputs and concurrent commands | Transactional constraints and row/scope locks | Parameterized SQL, least-privilege roles, idempotency, migrations, backups |
| TB-04 | API/worker to document store/scanner | Uploaded bytes, names, MIME claims, scanner/storage failure | Protected opaque storage and clean-scan decision | Size/type bounds, malware scan, encryption, no public path, fail closed |
| TB-05 | API to routing/map providers | Coordinates and provider availability | Normalized route response and client display | Private/reviewed endpoint, timeout/rate limit, no provider authority over ride/fare |
| TB-06 | Worker to FCM/APNs/pager | Provider credentials, delay, duplication and response bodies | Outbox/event state and restricted case state | Minimal identifiers, retries/dead letter, no sensitive payload/logging |
| TB-07 | Build/CI to release/deploy | Pull requests, dependencies, runners and registries | Reviewed commit, locks, signed artifacts and digest deployment | Pinned actions, scans, SBOM, provenance, protected environments |
| TB-08 | Staff and operator procedures | Human error, insider abuse, shared accounts | Scoped operations process and independent approval | Named accounts, least privilege, access review, dual control, drill/audit |
| TB-09 | Backup/export/cache boundary | Copies outside primary-row retention | Approved retention and legal-hold policy | Encryption, inventory, expiry, restore isolation, deletion reconciliation |
| TB-10 | City/operator boundary | Valid staff from another authorized scope | Resource's authoritative market/city/operator | SQL filtering before count/pagination, opaque 404, negative isolation tests |

## 5. Threat actors

* Unauthenticated internet attacker or automated abuse client.
* Malicious or compromised passenger, driver or applicant account.
* Compromised mobile device, rooted device, browser extension or copied token.
* Staff member acting outside their city, operator, permission or approved task.
* Privileged insider, contractor or compromised production credential.
* Malicious uploaded file or content intended to exploit reviewers/scanners.
* Dependency, build-runner, action, image, registry or signing-key compromise.
* Provider outage, compromised provider, DNS/routing interception or stale graph.
* Accidental operator error, concurrency race, retry storm or partial deployment.

## 6. Threat and control register

### Identity and session threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-ID-01 | Enumerate accounts through registration/login/reset timing or messages. | Generic auth errors, Argon2 dummy verification, reset hashing before lookup, generic recovery acceptance and hashed-key rate limits. | Statistical timing/abuse test in hosted staging; malformed-schema responses must remain identifier-independent. |
| TM-ID-02 | Reuse a stolen, expired, wrong-audience or revoked token/code. | Fixed token issuer/audience/type/algorithm, live session/status checks and rotating refresh; offline recovery uses independent 100-bit codes, domain-separated digests, expiry, whole-set rotation, row locks, one-time consumption, account-wide revocation, staff exclusion and limits. | Device/browser and concurrent code replay/rotate matrix, clock skew, logout/reset/suspend races, secret-redaction and hosted abuse tests, safe-storage research and compromised-account support runbook. |
| TM-ID-03 | Substitute a mobile token for operations authority. | Separate operations audience/parser/session and scoped grants. | Negative test every operations family with passenger/driver tokens. |
| TM-ID-04 | Bypass operations MFA or replay TOTP/recovery code. | Encrypted factors, counter replay prevention, single-use recovery, recent-MFA window. | Production enrollment/recovery drill, concurrency tests, encryption-key rotation procedure. |
| TM-ID-05 | CSRF or refresh-token theft in operations browser. | Secure HttpOnly SameSite cookie, path scope, CSRF binding/rotation, exact HTTPS origin. | Browser DAST for login/refresh/logout/step-up; CSP and hosting acceptance. |
| TM-ID-06 | Shared/bootstrap administrator becomes routine global authority. | Scoped `/operations`; legacy `/admin` omitted and rejected in staging/production. | Zero production callers, final route removal decision, safe nationwide incident authority. |

### Authorization and isolation threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-AZ-01 | IDOR reads/mutates another participant's ride, payment, application, case or document. | Ownership/participation predicates and opaque not-found responses. | Generated cross-user matrix across every object route and state. |
| TM-AZ-02 | Staff uses valid grant against another city/operator. | Scope expansion, permission checks, SQL-before-count filters, scoped audit. | Multi-city negative tests for list/detail/command/count and changed assignments. |
| TM-AZ-03 | Pagination/count reveals hidden records. | Scoped filters applied before count and limit in reviewed operations APIs. | Query-level regression for every restricted collection and analytics cell. |
| TM-AZ-04 | Driver self-approves, verifies vehicle or becomes dispatch eligible through client state. | Server review decisions, scoped vehicle verification, city authorization and availability checks. | Full application-to-dispatch negative workflow, stale/edit-after-review tests. |
| TM-AZ-05 | Market-scoped staff suspends a nationwide account outside authority. | Dedicated platform-admin permission; target-market association; complete permission coverage across every associated market; unrelated and partial-scope requests fail closed; recent MFA, idempotency, controlled case reference, typed-confirmation console and fixed-field audit; legacy action disabled in production-like environments. | Test concurrent history/grant changes; run independently observed production-like containment/recovery and access-review drills. |
| TM-AZ-06 | A revoked/expired grant remains usable, or staff self-grants, escalates scope, removes its own authority, or allows the last administrator to expire. | Active grants are reloaded/expanded per request; backend self-create/self-revoke rejection, closed role/scope schema, market authorization, recent MFA, audit, typed-confirmation console, expiry visibility and authoritative reload. | Concurrent revocation and last-admin/expiry tests; independent approval, roster linkage, recertification reminders, hosted browser/MFA acceptance, production access review and joiner/mover/leaver drill. |

### Ride, location and physical-safety threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-RD-01 | Assign wrong/ineligible driver or vehicle. | City/service/authorization/vehicle/location eligibility and transactional offer acceptance. | Multi-replica contention, stale location, credential expiry and race tests. |
| TM-RD-02 | Passenger sees online taxi positions or tracks unassigned drivers. | Passenger contract exposes offers/assignment outcomes, not fleet positions. | API/schema and UI network inspection with populated nearby drivers. |
| TM-RD-03 | Driver spoofs location or replays stale updates. | Ownership, freshness, accuracy and city service-area rules; no client assignment authority. | Field spoof/impossible-speed policy is incomplete; fraud controls required. |
| TM-RD-04 | Route provider manipulates fare, assignment or ride state. | Provider output is normalized; fare/assignment remain backend policy. | Malformed/long/looped route fuzzing, timeout/degradation and graph acceptance. |
| TM-RD-05 | Duplicate/out-of-order retry causes double ride, offer or completion. | Idempotency, state machines, locks and leases. | Multi-instance retry storm and failover test at every sensitive command. |
| TM-RD-06 | Safety UI or an assigned-ride signal implies emergency dispatch that does not exist. | Explicit non-emergency contract; six role-bound closed signals only; no free text/contact exposure; generic push refresh; separate controlled safety path. | Localized device comprehension test and staffed escalation/provider-outage drill in every launch language. |

### Payment and economic threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-PY-01 | Client alters fare, currency, fee, recipient or payment status. | Versioned server config and immutable quote/ride/payment/earning snapshots. | Property tests, cross-version tests and production config dual review. |
| TM-PY-02 | Reuse transfer evidence or verify wrong claim. | Unique claim/reference rules, locks, idempotency and scoped reconciliation. | Controlled statement import/reconciliation simulation and real micro-test. |
| TM-PY-03 | Duplicate refund or amount exceeds authoritative payment. | Transactional conservation checks and immutable refund records. | Concurrency, partial-failure, rounding and operator-funding tests. |
| TM-PY-04 | Malicious staff changes recipient then verifies own transfer. | Versioned recipient/capability lifecycle, permissions and recent MFA. | Dual control is incomplete; add separation-of-duties tests and staff UX. |
| TM-PY-05 | Cash custody or payout is falsely represented as settled. | Cash ride settlement and driver earning records only. | Physical cash policy and operator-driver payout accounting are not implemented/accepted. |

### Sensitive data, files and case threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-DT-01 | Path traversal, oversized/polyglot or malware document reaches staff. | Opaque keys, body/file bounds, allowlisted media, private scanner, clean-only read, no-store. | Real scanner corpus, archive/polyglot tests, encrypted storage and browser download acceptance. |
| TM-DT-02 | Logs, metrics, geocoder, push, pager or WebSocket leak personal/case/location-intent data. | Fixed/minimal event fields, route-template-only request logs, backend-proxied bounded geocoding, no persisted queries, normalized logs and identifier-only notifications. | Automated sink inspection with canary secrets/PII/place queries and provider failure bodies; approve geocoder data handling and egress. |
| TM-DT-03 | Case list/detail leaks narrative or participant across scope. | Separate participant/restricted projections, scoped grants and fixed audit fields. | Cross-role/city matrix, assignment revocation and export/browser-cache tests. |
| TM-DT-04 | Retention deletes held data or leaves sensitive copies indefinitely. | Case legal holds, retention workers and driver-document erasure evidence. | Complete store/copy matrix, backup/cache/log expiry and time-shifted production-like tests. |
| TM-DT-05 | Analytics enables re-identification or arbitrary event injection. | Typed server events, approved dimensions and small-cell suppression. | Composition/differencing review, export restrictions and data-quality monitoring. |

### Platform, availability and supply-chain threats

| ID | Threat/abuse case | Current preventive/detective controls | Required verification and residual work |
| --- | --- | --- | --- |
| TM-PL-01 | SQL/command/template injection through API or operations fields. | Pydantic bounds/enums, parameterized SQL, no client-supplied authorization. | SAST, property fuzzing and authenticated DAST across all parsers. |
| TM-PL-02 | SSRF through routing, geocoding, pager, storage or provider configuration. | Deployment-owned URLs, startup validation, hosted HTTPS requirement, shared-public-geocoder rejection and no user-controlled provider URL. | Egress policy and staging SSRF tests including redirects/DNS rebinding. |
| TM-PL-03 | Dependency/action/image compromise enters release. | Hash-locked Python, Gradle wrapper validation and commit-pinned actions. | All-ecosystem scans, image scan, SBOM/provenance, signing and remediation SLA. |
| TM-PL-04 | Secret committed, logged, embedded in web/mobile or leaked in artifact. | Source credential scanner and deployment secret boundaries. | Artifact string scan, runner/log review, secret-manager inventory and rotation drill. |
| TM-PL-05 | Database/provider outage causes unsafe stale success. | Readiness, explicit dependency errors, bounded retries and dead letters. | Chaos/soak, failover, RPO/RTO restore and user-visible degraded-mode tests. |
| TM-PL-06 | Worker duplication or lease failure produces duplicate effects. | Transactional leases/idempotency and separated worker role. | Multi-replica kill/restart/clock tests for all worker loops. |
| TM-PL-07 | Unsigned or mismatched client/web/container is deployed. | Release config validation, release evidence generator and digest-oriented manifest. | Clean-commit CI, signed artifacts, store verification, web immutable hosting and attestation. |

## 7. Required security test packs

Each pack is independently runnable and produces machine output plus a short
human disposition. A passing scanner does not replace authorization tests or
independent review.

| Pack | Earliest phase | Content | Blocking result |
| --- | --- | --- | --- |
| SEC-01 identity/session | T1–T3 | Token audience/type/expiry/revocation, MFA replay, refresh rotation, CSRF, rate limits | Any authority bypass or reusable revoked credential |
| SEC-02 participant IDOR | T2–T3 | Every owned object crossed among passenger, driver, applicant and unrelated user | Any hidden object read/count/mutation |
| SEC-03 staff scope | T2–T3 | Every operations list/detail/command across role, permission, city, operator and revoked grant | Any cross-scope result or count leak |
| SEC-04 state/concurrency | T1–T5 | Idempotency payload binding, stale versions, duplicate workers, payment/offer races | Duplicate money/assignment or silent lost update |
| SEC-05 file/data sinks | T3–T5 | Upload corpus, scanner/storage failure, downloads, log/metric/push/pager/event canaries | Executable file exposure or sensitive sink content |
| SEC-06 browser/mobile | T4–T5 | CSP, cookies, CSRF, XSS, storage, deep links, screenshots, rooted/debug builds | Credential exposure or privileged browser action |
| SEC-07 infrastructure | T5 | TLS/DNS/host/origin, egress, network policy, IAM, secrets, backup isolation | Public database/private service or broad credential |
| SEC-08 supply chain | T0–T5 | SAST, secret scan, dependency/image scans, SBOM, provenance/signature checks | Unaccepted critical/high finding or untraceable artifact |
| SEC-09 DAST/fuzz | T5 | Authenticated API/browser scans, malformed JSON/multipart/coordinates/headers | Crash, injection, auth bypass or sensitive error |
| SEC-10 incident/restore | T5–T7 | Credential rotation, revoke/contain, audit export, restore/failover, notification decision | Uncontained access, data loss or missed escalation |
| SEC-11 independent test | Before T8 | Threat-model review and penetration test with retest | Open launch-impacting finding |

## 8. Test execution rules

1. Use synthetic accounts/documents/location/money before a separately approved
   real-data exercise.
2. Generate at least two markets, two cities per market, two operators, every
   operations role, unrelated participants, revoked grants and expired sessions.
3. For each protected endpoint, test missing, malformed, mobile, operations,
   wrong-role, wrong-scope, revoked and valid credentials.
4. For each collection, compare body, status, total, page boundaries, timing and
   aggregate output; a hidden row must not alter an observable count.
5. For each command, test same-key/same-payload replay, same-key/different-payload
   conflict, stale version, concurrent execution, process death and retry.
6. Place canary values in every sensitive field and assert they never appear in
   logs, metrics, traces, push, pager, WebSocket hints, filenames or errors.
7. Preserve scanner versions, commands, target commit/image digest, config hash,
   timestamps and raw reports in restricted release evidence.
8. Never run load, fuzz, DAST or exploit tests against public/production systems
   without written target authorization, rate/impact limits and a stop contact.

## 9. Security stop conditions

Immediately stop the test or rollout, preserve evidence and begin incident
handling for:

* cross-account, city, operator or role access;
* operations authority without a valid operations session/grant/MFA;
* wrong driver/vehicle assignment or client-authoritative eligibility;
* money creation, duplication, misdirection or unreconciled destructive action;
* sensitive data in a public response, log, metric, event, notification or file;
* executable/malicious document made available to a reviewer;
* active access after intended revocation/containment;
* critical dependency/image/secret/provenance finding in the candidate;
* database corruption, unrecoverable loss or failed legal hold; or
* unsafe stale success during a dependency outage.

## 10. Evidence and acceptance

Every finding records: threat/test ID, affected release/config, severity, exact
reproduction, data exposure, containment, owner, fix, regression, independent
retest, residual risk, expiry and approving security owner. Critical/high risk
cannot be waived indefinitely or by the feature author alone.

Repository completion requires all applicable automated packs wired to CI and a
reviewed threat model. Deployment acceptance additionally requires the immutable
candidate, production-like staging evidence, credential rotation and incident
drills, clean or explicitly time-bounded reports, independent penetration retest,
and named security approval. Legal/privacy, city, finance and safety owners retain
their separate approval responsibilities.

## 11. Review triggers

Re-review this model for any new payment provider, communication channel,
identity/recovery method, staff role/scope, country/market, sensitive data field,
analytics dimension, document type, external provider, hosting boundary,
microservice, public callback, build/signing path or material incident. Also
review before each T8 pilot candidate and at least annually while operating.
