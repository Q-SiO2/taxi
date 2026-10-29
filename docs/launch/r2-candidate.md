# R2 local source candidate — 23 October 2026

Status: **local source candidate preserved; R2 acceptance remains open**.
This checkpoint implements the next bounded packet in the
[real-world launch plan](../real-world-launch.md), following the
[R0 baseline](r0-baseline.md). It does not accept production or transfer historical
alpha results to a new candidate.

## Exact source and preservation

| Item | Recorded identity |
| --- | --- |
| Local candidate commit | `45c491a4615d466c74c4bb0ca46fd6d55488ad7f` |
| Candidate tree | `6f2c2dbf6e096af613bd3d84f4e7bd01f827b137` |
| Parent / original checkout HEAD | `2835c8aa7f5e97a17afcdbe647fe589cbd0421e1` |
| Candidate branch | `codex/real-world-r2-baseline` in an independent local clone |
| Local directory | `.tools/real-world-launch/source-candidate-r2-20261023` |
| Captured scope | 3,340 non-ignored files: application, backend, tests, infrastructure, assets, documentation and explicit root metadata |
| File manifest digest | `4c33007c63a76e9ea571dafea6e798d2d3fab7d11d63bfdb8ffbc2cc53cf8a8c` |
| Original checkout | HEAD and staged-file inventory preserved; no original staging or commit |
| Publication/signing | No remote configured, no push, no remote CI run, unsigned local commit |

The snapshot intentionally preserves existing application work as well as this
packet's fixes. Capturing it does not constitute independent review of every
pre-existing delta. Git identity uses `TaxiMobile Local Candidate`; this is not an
owner signature. The original alpha APKs, staging deployments, volumes, protected
records and credential recovery are unchanged.

The [source comparison](r2-alpha-source-comparison-20261023.json) established:

- All 415 retained web v10 source inputs match current bytes.
- All 298 retained API v6 upload inputs match current bytes.
- Native v23's 415-input manifest differs in the previously disclosed web-only
  `ApplicantApplicationEditor.kt`; its APKs and native behavior were not rebuilt.

These comparisons cover manifest-listed paths, not new unlisted files or fresh
remote runtime observations. File hashes were checked during capture and again
before the local commit. A later documentation checkpoint in the main workspace
is outside this frozen commit; subsequent changes need a successor candidate.

## Two evidenced fixes

**Credential archive discovery.** The source credential gate previously trusted
any successful parent Git discovery. An ignored source archive inside a parent
checkout could therefore discover zero files and pass without scanning its source.
A synthetic reproduction confirmed zero discovered files and zero findings for
a source file containing a private-key marker. The gate now requires the inspected
directory to be the actual Git root; otherwise it uses the documented archive scan.

The new explicit `--include-untracked` mode scans non-ignored new source/configuration
during candidate preparation. Default CI behavior remains tracked-only. Regression
cases verify nested archives, untracked-source detection, unread ignored local
secrets/generated output and rejection of forbidden candidate filenames before
reading their contents. The gate prints paths and rule names, never matched values.

**Portable handoff links.** The isolated documentation check found two links to
ignored local APKs. The active handoff now links to their retained public artifact
record, preserving exact hashes and local archive locations. Documentation validation
can run from the source candidate without copying compiled APKs into Git. The initial
failure remains recorded; no validator assertion was weakened.

## Checks and provenance

The [candidate/check record](r2-local-verification-20261023.json) and
[generated release identity](r2-release-evidence-20261023.json) retain the exact
candidate and local evidence digests. Reports were written outside the candidate
so evidence generation did not dirty its source tree.

- **16 focused tests pass** in the isolated candidate: 14 source-credential tests
  plus two release-evidence tests. The new credential tests also passed in the
  original workspace before capture.
- Candidate documentation, expanded credential scan and CI-definition security
  checks pass. A scan including untracked source also passed in the original workspace.
- Candidate was clean after commit and the existing release-evidence generator
  emitted `SOURCE_CANDIDATE` without `--allow-dirty`.
- R0's 983 backend unit tests remain their earlier dirty-tree result; they were not
  rerun or relabelled as a complete immutable-candidate suite. No Android/iOS/web
  rebuild, hosted request or production mutation was performed in this packet.

## Next bounded work

1. Reconcile the frozen source delta and repository publication/CI configuration,
   then obtain actual immutable remote CI for the reviewed candidate. A clean local
   commit does not satisfy GAP-001/013/033 or T0 promotion on its own.
2. Run appropriate current-candidate API/PostGIS/contract/release checks and repair
   observed failures. Preserve current failed observations and avoid rebuilding
   unchanged alpha artifacts solely to inflate counts.
3. Complete signing, actual Android/iOS resources, provider and deployment ownership
   through the [R1 decision packet](r1-decisions.md). First-city/operator and available
   release resources have been requested; unresolved facts remain pending.

R2 is not closed: independent review, full candidate CI, signed Android/iOS releases,
supported upgrade behavior and broader supply-chain evidence remain. The active
real-world goal retains all R3–R12 work. No process from this packet remains running.
