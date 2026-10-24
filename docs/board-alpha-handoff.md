# TaxiMobile - board alpha handoff

## Current delivery - 23 October 2026

Use **native v23 + live web v10 + recovered API v6 source** for board review.
[Integrated evidence](redesign/board-alpha-evidence/release-v23-r2-integrated-verification.json)
passes two synthetic cash journeys and seven presentation beats at **16:22 / 11:07**.
Each ride has eight successful business requests exactly once, corroborated by
Railway traces and fresh server reads. Same-process rebooking, quote resume and
controlled radio recovery pass. Driver ends offline; pending cash is zero.

The first run has a disclosed observer stop and deliberate same-ride continuation,
plus normal applicant sign-in after expiry. Its recovery-note metadata writer had
a bookkeeping error; the original native journal, screenshots and independent
request trace are intact, and the later consolidation is explicitly identified.
Neither timing is an uninterrupted recording or a seven-minute guarantee.

## Run the candidate

| Surface | Exact artifact or entry |
| --- | --- |
| Passenger Android | [Native v23 artifact record](redesign/board-alpha-evidence/candidate-native-v23.json), SHA-256 `d230aef6501397adc7628931a94ea7f67b6459277c573e694fb023641a7e8390` |
| Driver Android | [Native v23 artifact record](redesign/board-alpha-evidence/candidate-native-v23.json), SHA-256 `5574f9e20ef5ade1621f58683712b6eb78f556ca828c23d83689a084137657e3` |
| Operations | [Hosted web](https://alpha-web-staging.up.railway.app/) - web v10 deployment `da158b10-2d82-468e-b1f1-cffba5c32ee4` |
| Applicant | [Hosted applicant](https://alpha-web-staging.up.railway.app/apply/) - shorthand `/apply` also redirects correctly over HTTPS |
| API | [Staging API](https://alpha-api-staging.up.railway.app) - deployment `8b03ad50-ba24-4d38-88b3-dc5321cd77cd`, frozen API v6 authored source |

The artifact record retains local archived paths under `.tools/alpha-delivery/native-v23/`:
`androidApp-passenger-debug.apk` and `androidApp-driver-debug.apk`. Those ignored
binary files are available in the presentation workspace and are not source-checkout
dependencies; verify their hashes before installing them.

These are local debug alpha APKs targeting isolated staging, not store-signed
public releases or public download endpoints. Use the protected ignored cohort
record for synthetic sign-in/MFA; never copy credentials into docs, slides,
screenshots or URLs. Only named API31 passenger/API35 driver emulator fixtures
were accepted. Their current running state must be checked before presenting;
do not infer it from historical PIDs. The physical phone is deferred.

After final verification, [both owned emulators were normally stopped](redesign/board-alpha-evidence/release-v23-r2-owned-fixture-shutdown-20261023.json)
and their GPS feeder ended to release local resources. Installed apps/data are
retained and both font settings were 1.0. Boot and warm these exact fixtures
before the next presentation; no snapshot-restoration claim is made.

Follow [the presenter script](board-demo.md): warm the devices, verify an actual
fresh Casablanca driver fix and enabled online control before the timer, prepare
the passenger fare before taking the driver online, and accept the private offer
before its deadline. Keep clocks unchanged during the trip. Sign in to browser
portals shortly before their beats; page reload signs the applicant out, and a
rejected/expired session requires normal sign-in.

## Current ten-gate acceptance index

| Gate | Demonstrated scope | Remaining boundary |
| --- | --- | --- |
| AG-01 Design | Four selected actual styles; selected native widths, Arabic driver surfaces and hosted timeline renders. | Owner visual acceptance; broader view/state review. |
| AG-02 Passenger | Two new exact-v23 cash trips, quote resume and same-process rebooking. | Broader no-supply, cancellation, draft and uncertain-command states. |
| AG-03 Driver | Eligible synthetic on-demand/private-offer/trip/cash flow and populated financial views. | Full restriction/onboarding/recovery and field coverage. |
| AG-04 Authority | Eight native commands per ride once; independent successful HTTP traces and server-owned amounts/status. | Full negative, concurrency and idempotency acceptance. |
| AG-05 Location | Native synthetic fresh fix/completion lookup and observed 14-second radio interruption/restoration. | Physical permission, foreground/background and field navigation. |
| AG-06 Operations | Normal MFA, authorized Casablanca applicant read and matching applicant timeline. | Extra roles expired; optional financial/support controls and every operations flow remain separate. Earlier resubmission evidence retains its original identity. |
| AG-07 Railway | Five exact healthy deployments; 103 web HTTP checks/all 93 assets; HTTPS redirect and applied credential/MFA recovery. | Trial credit/future uptime not guaranteed; no full forensic clearance. |
| AG-08 Android/localization | 389 JVM/311 Android-host and 75 JS/75 Wasm build checks; selected actual EN/FR/AR/RTL and width/material observations. | Physical Android, iOS, full accessibility and all combinations. Browser AX can be stale after preferences. Arabic routing narration uses English fallback. |
| AG-09 Rehearsal | Two qualified final-pair seven-beat records; independent requests, same process and radio recovery. | First-run interruptions retained; no continuous video or timing guarantee. |
| AG-10 Handoff | Exact APKs, deployed URLs, evidence, presenter instructions and later roadmap. | Owner presentation decision and pilot/public gates. |

The 213-view inventory does not establish runtime acceptance of every page.
Do not convert these scoped results into an overall launch-readiness percentage.
Trial remains unchanged, both volumes are preserved, and no expired staff role
was renewed. API/worker images were rebuilt with qualified frozen-source provenance;
DB retains its exact image/volume. [Recovery details](redesign/staging-recovery.md)
and [the roadmap](roadmap.md) retain later pilot, real-money, legal/provider and
public-launch gates.

[Earlier handoff and fallback evidence](history/board-alpha-handoff-before-final-v23-20261023.md)
are retained historically; their old provider-paused/current-version statements
are superseded by this handoff.
