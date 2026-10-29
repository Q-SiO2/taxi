# Operations session recovery and web release — 23 October 2026

Status: **local protocol, production package and partial Chrome boot passed; CI correction in progress**. This R2/R8/R9
packet follows the [member-register rehearsal](member-register.md); it does not
change the full [real-world launch scope](../real-world-launch.md).

## Evidence that selects the work

[CI run 224](member-register-ci-terminal-20261023.json) for source
`e73e6b4304325dde90cf9599418891e38b83890b` completed with successful backend,
Android, unsigned iOS, documentation/provenance, wrapper, Gradle dependency
submission and complete dependency review. The web tests and production build
passed, but packaging rejected `originJsWebApp.js`: **6,984,560 bytes** against
the reviewed **6,900,000-byte** ceiling. It is not an overall passing candidate.

The previous actual browser rehearsal also returned `401` on sign-out after
the ten-minute access window, while the client returned to sign-in. The client
called logout directly instead of using its established access-refresh protocol.
Local clearing did not establish server refresh-session revocation.

## Source correction

- Logout now uses the same bounded access-refresh path as other operations
  requests: one initial `401`, one refresh and one command with the replacement
  access token. The replacement is published before the command, even if that
  command fails. Unknown transport/refresh results, non-`401` rejections and
  cancellation do not trigger refresh loops or command replay.
- Unconfirmed server revocation still clears local access and reports that
  distinction in EN/FR/AR. It no longer implies that expiry of the short access
  token is sufficient to revoke the longer refresh session.
- The first standalone web text-selection container is replaced by an existing
  read-only outlined field for each complete driver ID, with an explicit localized
  label and LTR direction. The actual Arabic render shows the complete selected
  reference. Clipboard copying remains unverified: the equality check returned
  false while the observation context changed. No accessibility acceptance follows.

The minifier experiment on a prior October 22 bundle saved only about **17 KB**
with an additional pass, including an ES2020 variant. Those diagnostic artifacts
are not current-source evidence and do not justify changing the shipping
compiler/minifier configuration. The current production JS is **6,935,862 bytes**,
48,698 bytes smaller than the rejected predecessor, but still 35,862 bytes above
the old ceiling. The bounded [scope review](../deployment.md) raises fallback JS
to **7,000,000 bytes**, leaving 64,138 bytes of headroom (+1.59% against v8's
measured bytes). Loader, Wasm and total limits stay fixed. This is an explicit
budget revision for added roster/session functionality, not a claim that the
older limit passed or that startup performance is accepted. Gzip9 is
**1,646,781 bytes**, +22,474 against v8. No dependency changes.

## Verification

Two actual PostGIS/HTTP scenarios pass, one using the hosted secure-cookie/CSRF
protocol and one using the explicit test/development JSON refresh protocol.
Each rejects an expired bearer, rotates refresh, revokes the replacement session,
rejects its access and refresh credentials, and confirms no active session in
that family. Normal logout is not marked as refresh reuse.

Five client protocol cases cover the expiry sequence, no unnecessary refresh,
non-auth/transport/cancellation boundaries, unknown refresh and bounded repeated
rejection. All **84 JS and 84 Wasm browser tests** pass, including these five
cases per target. The first client build was deliberately cancelled before the
copyable-ID source change; it is not a pass. A combined development/production
invocation later hit Gradle's undeclared shared-output dependency after the tests
and development build passed. Production verification uses its separate invocation,
as CI already does; neither failed invocation is reported as an overall pass.
At this source checkpoint the separate production invocation has compiled the JS
bundle and is still optimizing Wasm. Full packaging and the bounded Chrome
release-boot checks are pending. Its running state must not be interpreted as a
successful distribution or overall CI result.

The localhost browser harness reuses the existing synthetic member database and
MFA factor. For the expiry scenario only, its first bearer is issued with one
minute remaining; the real clock, JWT validation and normal refresh bearer
lifetime are unchanged. This is synthetic expiry verification, not a physical
device, provider or ten-minute field observation. The actual browser submitted
expired-access logout `401`, refresh `200`, then replacement-access logout `200`
and displayed sign-in. Database readback confirms a shared refresh family, old
rotation, replacement revocation and **zero active sessions**; ordinary logout
was not classified as refresh reuse. Membership remains three rows with exactly
one create and one update audit from the preceding rehearsal. No roster command,
MFA recovery or seed was replayed.

The evidence includes the [selected ID](session-recovery-evidence/readonly-driver-id.png)
and [sign-in after revocation](session-recovery-evidence/expired-access-logout.png).
The owned local API, web server and PostGIS were stopped after readback; their
logs and synthetic data remain preserved.

The [machine-readable verification](session-recovery-verification-20261023.json)
binds these observations, 371 compilation inputs and retained reports to the
source packet. Infrastructure tests total **277 passing**; mobile/web API,
CI-security, source-credential and documentation checks pass. Candidate capture
also verifies every recorded compilation input against the isolated source clone.

The browser accessibility-tree loss after dialog dismissal remains an observed
R9 issue requiring root-cause and real screen-reader/focus verification.

## Hosting preparation

The [fresh staging inventory](staging-upgrade-preflight-20261023.json) uses the
previously authorized CLI because the connector is again unauthorized. Five
latest deployments are successful and both 500 MB volumes are preserved; the
active volume reports about 219 MB used. This establishes metadata only.
No deployment, volume, billing, staff grant, credential or MFA change was made.

After the source passes its own CI, prepare the schema `0053` upgrade with a
protected backup, isolated restore, owner/runtime privilege checks and matching
API/worker artifacts. Reuse the existing staging authorization and Trial limits.
Do not replay the previously applied credential/MFA recovery or infer production
funding from the current staging metadata.

## Published source checkpoint

The [candidate record](session-recovery-candidate-20261023.json) identifies
`aeff4a25d1d07ab8f6762fad9826af90cfb5708d`, tree
`c26cd2cd34e83b52b734438e2d9099886e9751ec`, published to
[draft PR #74](https://github.com/Q-SiO2/taxi/pull/74). All 371 recorded compilation
inputs match the clean isolated clone; the original workspace HEAD/index remain
preserved. [CI run 226](https://github.com/Q-SiO2/taxi/actions/runs/40040360195)
is in progress. Documentation/provenance and wrapper checks passed at this
checkpoint; the remaining jobs and separate local production distribution are
running. No overall CI or packaging pass is claimed. Resume those exact runs
before starting another build. This post-publication record does not change the
published source SHA.

## Terminal local release and subsequent CI finding

The [terminal local record](session-release-terminal-20261023.json) supersedes the
running-build observation: the same production invocation finished successfully
in **21m21s**. All 371 compilation inputs still match. Packaging passes with
**93 assets / 29,834,826 bytes**, excluding three source maps; each packaged asset
was rehashed. JS is 6,935,862 bytes, Wasm loader 543,417, application Wasm 7,626,289
and Skiko Wasm 8,652,729, within the explicitly reviewed limits.

The existing Chrome collector passes its four supported applicant/operations,
required-upgrade and failed-preflight scenarios. This is bounded boot evidence,
with no full browser-matrix, catalog-case, performance or T4 acceptance.

CI run 226 subsequently failed the development dependency audit on three new
`filelock 3.32.2` advisories; the runtime lock audit passed. The
[dependency correction](dependency-refresh.md) records the precise scoped update
and fresh verification. No hosted rollout follows from these local results.
