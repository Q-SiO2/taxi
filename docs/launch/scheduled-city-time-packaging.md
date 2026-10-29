# City-time packaging and artifact verification

27 October 2026. Source follow-up to `2e9275a`; the full R0-R12 launch goal and
existing acceptance authorities remain in force.

[CI 254](scheduled-city-time-ci-terminal-20261026.json) passes six required jobs,
including 1,482 backend cases, eight disposable TLS probes with cleanup and both
unsigned iOS Release simulator products. It fails the web size gate and Android
artifact verification. Neither local successful compilation nor those six jobs
accepts the complete candidate. Do not retry that immutable source unchanged.

## Wasm initialization

The complete compatibility build succeeds, but its Wasm JavaScript loader is
1,275,557 bytes locally / 1,275,564 in CI, above the unchanged 700,000-byte cap.
The JS fallback is 6,953,397 bytes, below its unchanged 7,000,000-byte cap. The
packager rejects the candidate before a Chrome boot smoke begins.

A top-level lazy delegate retained the named-zone cache's initializer in Wasm.
The cache now lives behind private object initialization, preserving its named
zones, immutable cached set and existing invalid-data behavior. A fresh production
link removes the unused timezone-module import and probe from the operations
entry point; the core module remains. This generated-import evidence is not a
substitute for complete optimized packaging, budget checks and actual boot.
Browser tests must still load real rules when the formatter is used.

## Android compiler cohorts

Both local and CI minified role APKs assemble. Enabling API-24 Java desugaring
adds a library DEX with an L8 classfile marker and a separate full-release R8 DEX
marker without the application's mapping ID. The previous verifier required that
ID on every R8 marker and rejected the valid library output.

The repair still requires a separate application R8 marker matching the exact
mapping ID, reviewed compiler 9.1.56 and full-release DEX mode. An unmapped R8
marker is permitted only alongside exactly one L8 marker in the same DEX, with
the pinned compiler, configuration
`com.tools.android:desugar_jdk_libs_configuration:2.1.5`, release modes and API 24.
The application must declare that same desugaring context. A library cohort
cannot bless missing/old application markers, a different mapping, another DEX,
duplicate cohorts or an unreviewed compiler/configuration. Existing archive,
identity, hashing, mutation, signing and non-distribution guards remain.

The retained 24-test baseline has one failure and one error: it rejects the valid
library pair and accepts an unsupported mapped-library combination. The repaired
full source/build-tool suite passes 121 tests, including the four new test methods
and their negative subcases. Re-inspecting the unchanged `2e9275a` APKs now passes
both packaged identities and scoped marker checks. These binaries do not contain
the later cache change and cannot accept that successor source. No rebuild is
needed to correct an observer's rejection of existing bytes.

## Browser functional startup allowance

The provider's first JS lookup was observed at 1,283-4,004 ms, while Wasm was
186-276 ms on this machine. A later functional run hit Mocha's default 2-second
timeout despite correct rule assertions. A test-only root hook gives the two
`ScheduledCityTimeBrowserTest` cases a bounded 10-second provider-startup allowance.
Other suites retain their existing 2-second default. A real Mocha execution checks
both the selected allowance and the unrelated default. The initial hook-loading
order failure is retained; registration uses the root suite before BDD globals
are installed. The hook is excluded from production sources.

Cold lookup measurements remain in the test output. This allowance is not a
customer latency target or performance acceptance. Actual supported-browser and
low-end-device latency remains an open gate; do not hide it behind functional
test success or claim that moving the cache improved cold parsing speed.

## Remaining evidence

The [27 October source-hash record](scheduled-city-time-packaging-verification-20261027.json)
passes 189 JVM, 363 Android-host, 86 JS and 86 Wasm browser cases, plus 121
source/build-tool tests and both debug role APKs. These sets overlap. The complete
optimized package passes unchanged caps with JS **6,953,397 bytes**, Wasm loader
**543,264 bytes** and **29,871,289 bytes** overall. Its 93 files exclude three
source maps and the test-only startup hook. Four Chrome boot/preflight scenarios
pass; they cover no T4 catalog case and do not accept the phase or deployment.

The successor `53d6531` now passes all eight required jobs in
[CI 256](scheduled-city-time-packaging-ci-terminal-20261027.json), including
current-source minified Android identity checks, web packaging/boot, 1,482 backend
cases and both unsigned iOS simulator products. Artifact hashes bind the tested
merge to the candidate's identical tree. Later review-binding changes need their
own verification; this accepts neither those changes nor physical/hosted operation.
Preserve CI 254 and the failed local observations. The friendly
city-local scheduling input remains the [next functional packet](scheduled-city-time.md#next-bounded-source-packet-scheduling-input).
Physical testing stays deferred by the owner, and hosting remains at the recorded
Trial capacity stop. No provider, operational, pilot or public acceptance follows.
