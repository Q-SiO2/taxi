# TaxiMobile — Delivery and Verification Workflow

This is the operational reading guide for moving a requirement through code,
verification and release evidence. It organizes existing decisions; it does not
change business policy or authorize deployment. Read [readiness.md](readiness.md)
for the dated assessment, [gaps.md](gaps.md) for open work, and [testing.md](testing.md)
for the full T0–T10 acceptance contract.

## 1. Choose the correct track

| Situation | Start here | Deliverable |
| --- | --- | --- |
| Understand what is built | `README.md` → `readiness.md` → relevant domain standing | Source/verification/acceptance distinction. |
| Implement or fix behavior | `roadmap.md` → owning domain → `architecture.md`/`implementation.md` | Focused implementation and meaningful tests. |
| Change HTTP or persistence | Owning domain → `api.md` → `database.md` | Consistent contract, deliberate migration, negative tests. |
| Change a screen | `design.md` → `ui.md` → relevant `extended_ui.md` screen | Approved visual language and backend-confirmed state. |
| Close a deployment blocker | Specific GAP entry → corresponding `testing.md` phase | Dated evidence and explicit owner acceptance. |
| Publish reports | `readiness.md` and current gap evidence → both TeX files | Rebuilt PDFs with identical status and limitations. |

Do not read every long document for a one-line fix. The complete-domain audit is
different: inventory all project areas and trace representative critical paths.

## 2. Start a task with a concrete contract

Record the following in the task/PR before changing behavior:

```text
Requirement / GAP / test-phase IDs:
Actor and city/operator scope:
Trigger and expected backend-confirmed outcome:
Current behavior and source evidence:
Allowed state transitions and rejected cases:
API, database, privacy and UI impact:
Acceptance checks and environment:
Policy decisions or dependencies still open:
```

Inspect Git status and relevant `AGENTS.md` first. Include untracked source when
checking whether a feature exists. Preserve other ongoing work. If code conflicts
with a normative rule, record the conflict and stop the affected implementation;
do not rewrite the requirement to bless convenient code. Independent read-only
audit/documentation can continue. Major policy or architecture decisions belong
to the project owner.

## 3. Implement one complete behavior slice

1. Confirm the permitted roadmap scope and the existing implementation path.
2. Define backend validation, ownership, transaction boundaries and state changes.
3. Add persistence only when necessary; document indexes, locks, migration
   preconditions and historical-data behavior. Do not repair records silently.
4. Wire the route and contract; reuse existing error and idempotency conventions.
5. Add shared Kotlin DTO/gateway/coordinator handling. Put native permissions,
   secure storage, connectivity, location and push hooks in platform source sets.
6. Add UI using existing tokens, components and localization. A command timeout
   leaves the outcome uncertain: reload authoritative state; do not imply success
   or replay a non-idempotent command automatically.
7. Test the successful flow, a meaningful rejection and relevant race/failure
   recovery. Include cross-city access rejection when scope is involved.
8. Update the owning docs, API/schema descriptions and the dated evidence record.

Backend authority applies to identity, eligibility, assignment, money and payment
status. Push/WebSocket events trigger authorized reads; they are not independent
proof of a state change. A provider-disabled flow must fail closed or show its
documented fallback.

## 4. Run checks at the right boundary

Commands below use PowerShell from `C:\Users\Q\Projects` and existing local
environments. First-time setup remains in [backend README](../backend/README.md),
[client README](../TaxiMobile/README.md), and [infra README](../infra/README.md).
Do not print `.env`, signing material, provider keys or recovery codes into logs.

### Fast source and documentation gate (T0–T2)

```powershell
backend/.venv/Scripts/python.exe infra/scripts/validate_docs.py
backend/.venv/Scripts/python.exe infra/scripts/validate_test_phase_evidence.py
backend/.venv/Scripts/python.exe infra/scripts/validate_mobile_api_contract.py
backend/.venv/Scripts/python.exe infra/scripts/validate_web_api_contract.py
backend/.venv/Scripts/python.exe -m unittest discover -s infra/scripts/tests -p 'test_*.py'
backend/.venv/Scripts/python.exe -m unittest discover -s TaxiMobile/scripts/tests -p 'test_*.py'
Push-Location backend
try { ./.venv/Scripts/python.exe -m pytest tests/unit tests/api } finally { Pop-Location }
```

Check each command's exit code. A later successful PowerShell command must not
hide an earlier failure. These commands do not establish PostGIS correctness.
Run only relevant subsets during a focused edit; execute the complete candidate
gates before promotion.

### Database and system gate (T3)

Use the existing guarded runner after local PostGIS setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File infra/scripts/test-portable-backend.ps1
```

This runner **recreates the explicitly named isolated `taximobile_ci` database**,
applies migrations and clones disposable databases for integration cases. It
must never target operational data. Coordinate with any other task using that
test database before execution. A source-only documentation audit may leave this
gate historical and explicitly report that limitation; a migration, transaction,
assignment or financial change requires fresh relevant database verification.

For HTTP load experiments use [testing_workloads.md](testing_workloads.md), whose
confirmation, synthetic-data and rate controls remain mandatory. Closed-loop
local workload success is not a peak-capacity result.

### Client and browser gate (T4)

```powershell
Push-Location TaxiMobile
try {
  ./gradlew.bat :shared:jvmTest --no-parallel --console=plain
  ./gradlew.bat :androidApp:compilePassengerDebugKotlin :androidApp:compileDriverDebugKotlin --no-parallel
  ./gradlew.bat :webApp:jsBrowserTest :webApp:wasmJsBrowserTest --no-parallel
} finally { Pop-Location }
```

Use the configured JDK/Android SDK and local Gradle cache. An offline cache miss
is an environment blocker, not a passing test. macOS/Xcode CI and physical iOS
acceptance remain necessary. Browser component tests do not replace end-to-end
applicant and operations workflows. Release/lint/signing/provider gates remain
in CI and platform release instructions; a debug compile is insufficient.
For any release-policy change, run the complete current/optional-update/obsolete/
malformed/unreachable client matrix in `testing.md` for the affected surfaces.
Record the policy revision and immutable artifact hashes; do not treat a forged
current-version header as authentication evidence.

### Staging and operational gates (T5–T10)

| Phase | Entry requirement | Exit evidence | Accountable function |
| --- | --- | --- | --- |
| T5 Hosted staging | Identified candidate and isolated target environment | Current-head restore, provider delivery, load/failure and security evidence | Infrastructure/security owners |
| T6 Staff rehearsal | Accepted staging and enrolled scoped staff | Synthetic money/case/document/incident workflows, handoff and recovery | Operations/payment/safety owners |
| T7 Closed field validation | Prior gates and approved bounded participation | Device, navigation, pickup/location, language and service observations | City operator and product owner |
| T8 Real-user pilot | Applicable P0 closure and explicit owner authorization | Bounded cohort, reviewed thresholds, support/rollback readiness and measured outcomes | City operator/release owner |
| T9 Public city launch | Pilot acceptance and resolved applicable P1 issues | Approved activation, live monitoring and stop criteria | Product and city authority |
| T10 Expansion | First-city closeout | Second-city isolation, configuration, staffing and capacity acceptance | National and city operators |

These are responsibility functions, not claims that a named person or roster has
been assigned. Tests do not automatically authorize a release. Retain the exact
phase safeguards in `testing.md`; a renamed “internal pilot” cannot bypass them.

## 5. Use explicit handoffs

An engineering handoff contains changed paths, verified commit/tree state,
migration/API impact, commands/results, known limits and open GAP IDs. It also
includes the generated API/migration/permission inventory and its candidate-
evidence hash when backend contracts changed. Promotion handoffs attach a
`validate_test_phase_evidence.py`-clean phase index and name the exact phase being
requested; an all-`NOT_STARTED` template is not evidence. A provider
handoff adds environment/configuration versions, credentials handled outside docs,
owner, expiry, controlled acceptance trace and fallback. An operations handoff
adds trained role, shift coverage, escalation, recovery and sign-off.

Evidence statuses advance as follows:

```text
Specified → Implemented in source → Locally verified → Clean-candidate CI
          → Environment/device/staff acceptance → Owner-approved promotion
```

“CI-wired” is a parallel description of a workflow definition, not an evidence
stage. Any relevant source, policy, configuration, provider or artifact change
invalidates affected evidence until rerun or explicitly reviewed. Never replace
an older dated result with a newer number unless the new run actually occurred.

## 6. Close a gap with evidence, not a status edit

```text
GAP ID and exact closure criteria:
Owner / independent reviewer where required:
Candidate commit and artifact digests:
Environment, city bundle and provider versions:
Scenario IDs, command, date and observed result:
Evidence location and retention/access classification:
Outstanding defects and operating restrictions:
Decision: open / partially addressed / deployment-accepted:
Acceptance date, expiry and invalidation triggers:
```

Keep detailed closure criteria in `gaps.md`, executable scenarios in `testing.md`
and `testing_workloads.md`, and the short percentage/evidence snapshot in
`readiness.md`. Cross-link instead of copying long test histories into every
domain. Retain historical evidence with its original head/date.

## 7. Maintain and publish documentation

For a domain change, update its owning specification first, then API/database
references if affected. Update `implementation.md`/`roadmap.md` standing only
when the evidence level changes. Recompute the readiness matrix only when the
scoped implementation or rating rationale changes; more test files alone do not
increase completion.

For report publication, build twice from `docs/` so references and page/slide
totals resolve:

```powershell
Push-Location docs
try {
  pdflatex -interaction=nonstopmode -halt-on-error taximobile_technical_report.tex
  pdflatex -interaction=nonstopmode -halt-on-error taximobile_technical_report.tex
  pdflatex -interaction=nonstopmode -halt-on-error taximobile_pitch_deck.tex
  pdflatex -interaction=nonstopmode -halt-on-error taximobile_pitch_deck.tex
} finally { Pop-Location }
```

Inspect the logs for undefined references and overfull boxes, render the PDFs,
and inspect all pages for clipping and readable tables. Keep TeX and PDF dates,
migration head, percentage, evidence limits and release decision synchronized.
The report and technical briefing remain communication outputs subordinate to
Markdown domain authority.
