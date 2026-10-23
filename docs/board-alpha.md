# Board alpha - current delivery checkpoint

## Current delivery - 23 October 2026

**The implemented native v23 / live web v10 presentation path passes within its
synthetic scope and is ready for owner board review.** The four choices are
Folded Streets, Street Press, Glazed Machine and Notepad. There is no separate
color menu or main taxi/city illustration. EN/FR/AR and RTL remain required;
map selection is the approved alpha location flow.

[Final integrated verification](redesign/board-alpha-evidence/release-v23-r2-integrated-verification.json)
checks two different completed **35 MAD cash** rides, eight successful native
business requests exactly once per ride, independent Railway traces, the same
passenger process, quote foreground recovery and an observed driver radio
interruption/restoration. Fresh server reads end with the driver offline and
pending cash zero. Normal Arabic staff MFA/Casablanca application reads and the
matching applicant timeline complete both seven-beat records.

Observed times are **16:22 and 11:07**, including agent verification overhead.
The first run includes a control-observer stop, explicit same-ride continuation
and normal applicant sign-in after session expiry. It is not a clean
uninterrupted run or a seven-minute promise. The original failure fields,
preflight/GPS/helper failures and a recovery-note bookkeeping correction remain
visible in the integrated record. No business request was replayed.

## Exact implementation and hosted evidence

- [Native v23 manifest](redesign/board-alpha-evidence/candidate-native-v23.json):
  415 archived inputs, four source deltas, **389 JVM / 311 Android-host** checks.
- [Web v10 manifest](redesign/board-alpha-evidence/candidate-web-v10.json):
  **75 JS / 75 Wasm** checks; 93 source-map-free assets within existing budgets.
  Its one later web-only source change replaces Arabic timeline text glyphs
  with vector circles. Native APKs are unchanged.
- [103 hosted HTTP checks](redesign/board-alpha-evidence/hosted-web-v10-20261023.json):
  every asset hash, relative HTTPS applicant redirect, headers and API boundaries.
- [Actual web visual review](redesign/board-alpha-evidence/web-v10-hosted-visual-review-20261023.json):
  all four Arabic timeline styles, French/English Notepad and live session continuity.
- [Normal staff MFA/read/logout](redesign/board-alpha-evidence/web-v10-staff-session-review-20261023.json)
  uses the preserved authenticator and baseline recruitment scope.
- [Fresh five-service identities](redesign/board-alpha-evidence/release-v23-r2-final-deployment-identities-20261023.json)
  confirm the exact final pair remains healthy with one active deployment each.
- [Selected native material/layout evidence](redesign/task-material.md) covers
  320/430 dp, four Arabic driver styles and qualified large-text map chrome.

## Next executable work

1. Use [the handoff](board-alpha-handoff.md) and [presenter script](board-demo.md)
   to review the actual candidate with the owner. Freeze this demonstrated path;
   do not rebuild unchanged binaries for observer failures or add another style.
2. Address concrete owner-rejected defects in bounded packets with affected
   checks. The 213-view atlas is an inventory, not runtime acceptance of every view.
3. Before a real pilot, complete the device/field, provider, operational,
   security/accessibility and legal acceptance required by [the roadmap](roadmap.md).
   Physical Android is explicitly deferred at present. iOS, real-money and public
   launch are not accepted by the synthetic demonstrations.

Railway stays on Trial with both existing volumes preserved. Credential/MFA
recovery is applied; do not repeat its cutover. Extra temporary staff roles
expired and were not renewed. [The recovery packet](redesign/staging-recovery.md)
records source/image qualifications and protected rollback boundaries.

[Previous checkpoint and historical evidence](history/board-alpha-before-final-v23-20261023.md)
retain their original artifact identities and do not override this checkpoint.
