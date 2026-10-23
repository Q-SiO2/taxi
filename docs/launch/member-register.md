# Operator member register — 23 October 2026

Status: **local source/runtime verification recorded; candidate review pending;
no hosted rollout**.
This R5/R8 packet extends the [admission gate](union-membership.md). It reuses
`CooperativeMembership` and the existing scoped `MANAGE_OPERATORS` permission;
it creates no second register, role template or real staff grant.

## Working launch model

The owner selects **Fès Taxi Union** as a generic name, with autonomous individual
taxis and union administration of membership/platform. No assumed separate union
transport permit is an engineering dependency. The [R1 record](r1-decisions.md)
keeps roster responsibility, service boundaries and other actual operating
decisions distinct from individual driver and vehicle eligibility.

## Implemented behavior

- Operations can list an operator's linked register, enroll a driver already
  associated with its city applications, and edit status, number and effective
  dates. It supports pending, active, suspended and ended records without deleting
  history, changing driver approval or interrupting an accepted trip.
- The backend checks current permission/scope and recent MFA before each write
  or replay. Writes use existing transaction locks, bounded idempotency keys,
  optimistic `updated_at` comparison and atomic audit. Audits include reason,
  status/date changes and whether a membership number changed, without copying
  that number. Read scope is applied before count and pagination.
- The web panel lives under the existing operator details, with policy review,
  paginated records, effective-date validation, explicit null clearing and
  version-conflict refresh. A failed or unknown response retains the command key
  for the same payload. A confirmed write closes the form even if readback fails;
  MFA recovery never silently replays the command.
- Shared native gateways recognize one exact backend membership rejection and
  display EN/FR/AR union-review guidance. Other server text is not surfaced.
  Drivers are told that accepted trips can still finish. No client membership
  state grants availability, assignment or acceptance.

The panel uses the existing four styles and localized resources. Browser/runtime
coverage must be recorded explicitly; sharing components is not proof that every
style, language, platform, page or accessibility state passed.

## Dependency comparison correction

Parent candidate `d499adb668426a0b9a37a15fa1da126f62ce9c13` passed backend,
Android, web, documentation, wrapper and unsigned iOS verification. Its dependency
review was cancelled while waiting for a missing head snapshot. That candidate
does not contain this staff-register packet.

The workflow now submits the resolved Gradle graph on same-repository pull
requests as well as pushes, and comparison waits for that job. Forks receive no
write-capable submission job and remain explicitly unaccepted by the review gate.
A standard-library read-only guard checks every API comparison page for snapshot
warnings both before and after vulnerability review. Missing/malformed warnings,
API errors, invalid revisions and unbounded comparisons fail the job. High and
critical vulnerability rejection remains enabled. This correction needs its own
remote CI result.

This follows the pinned [Gradle action integration guidance](https://github.com/gradle/actions/blob/9c971963bec38e04b3d30dcc455b5382be2fdbfb/docs/dependency-submission.md#integrating-the-dependency-review-action).
The pinned review action's [warning handling](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/main.ts)
and [comparison API implementation](https://github.com/actions/dependency-review-action/blob/a1d282b36b6f3519aa1f3fc636f609c47dddb294/src/dependency-graph.ts)
explain why increasing the timeout alone cannot establish a complete comparison.

## Verification and continuation

The coherent focused backend run passes **19 cases**: schema validation, scoped
listing/enrollment/editing, stale MFA, audit rollback, version conflicts,
concurrent duplicate/different keys, duplicate numbers, pagination and actual
dispatch selection/acceptance after staff suspension/reinstatement. The latter
also confirms that ending membership preserves an accepted ride.

The [verification record](member-register-verification-20261023.json) binds the
local reports and screenshots. Shared JVM tests pass **392 cases**, with **79
JavaScript browser tests** and **79 WebAssembly browser tests**. The coherent
Gradle build also produces the actual JavaScript development distribution.
Infrastructure checks pass **277 cases**; the final HTTP-error resource cleanup
has its own six-case guard rerun. Immutable successor CI remains separate.

The actual localhost browser uses MFA, selects an on-demand-only operator, loads
the register, enrolls one active synthetic driver with a start date, and suspends
another member while clearing its optional number. API readback and independent
database assertions confirm three members and exactly one create plus one update
audit. No fixture seed, MFA enrollment or business command was replayed to repair
an observer failure. An isolated API restart loads the route-read correction;
the existing fixture data and factor remain intact.

Selected populated register views were reviewed at 1280×720:

| Style / language | Retained screenshot |
| --- | --- |
| Notepad / English | [Static grayscale result](member-register-evidence/notepad-en.png) |
| Street Press / French | [Localized result](member-register-evidence/street-press-fr.png) |
| Glazed Machine / Arabic RTL | [RTL result](member-register-evidence/glazed-machine-ar.png) |
| Folded Streets / Arabic RTL | [RTL result](member-register-evidence/folded-streets-ar.png) |

This is selected-view coverage, not the full language/style/page/device matrix.
Native physical-device behavior, screen readers, complete keyboard focus, and
all policy/reinstatement/end/error states still need their named acceptance.

## Retained failures and limitations

- The first JVM test declaration returned a value instead of `Unit`, which JUnit
  rejected before executing that coordinator class. Its report is retained; the
  corrected coherent run passes all 392 shared cases.
- Browser automation initially changed a semantic field without committing the
  Compose input. Local validation and one rejected synthetic MFA attempt are
  retained. Real keyboard input, committed field-state inspection and a fresh
  challenge completed sign-in. No real credential recovery was performed.
- After dialog dismissal the browser's accessibility snapshot sometimes contains
  only containers, while screenshots and subsequent UI actions remain functional.
  Semantic field labels and focus recovery need browser/screen-reader investigation
  under R9. This observation does not establish whether the defect is in the
  application, framework or automation bridge; accessibility is not accepted.
- A broader local batch including the large parameterized published-route suite
  exceeded its finite 300-second runner budget. Its partial log is retained,
  remaining matching processes were checked absent, and the isolated 19-case
  focused run passed. The partial batch is not a full route-suite pass; fresh CI
  must verify the complete backend candidate.
- At rehearsal shutdown the UI returned to sign-in, but the server logout
  request returned `401`. Refresh-session revocation after access expiry needs
  its own regression; this observation is not a successful server-side logout.

No localhost fixture is a Fès pilot, hosted migration, real staff enrollment,
signed release or public activation. Earlier staging resources remain untouched.

The first actual operator inspection exposed an existing workspace blocker:
fixed-route list/fare reads threw an uncaught assignment conflict for an
on-demand-only operator, aborting the whole snapshot. These two reads now retain
exact scope/market checks while allowing empty or historical data without an
active fixed-route assignment. Write/publication authority stays unchanged.
Retain the initial HTTP 500 and the focused regression alongside the eventual
browser outcome; adding a synthetic assignment would conceal this defect.

Next: finish affected client/runtime checks; capture only intended files in the
isolated candidate; publish to the existing draft PR; inspect fresh exact-head CI.
Then prepare the controlled API/worker/schema upgrade with backup and compatibility
evidence. Staging remains on its prior schema until deliberately upgraded. Keep
the protected volumes, Trial limits and existing staff permissions intact.
