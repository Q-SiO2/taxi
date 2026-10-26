# Immediate-offer source-gate correction

26 October 2026. Focused successor to `e38ae7b`; no app, dependency, backend,
permission or hosting change belongs to this correction.

[CI 250](immediate-offer-review-ci-terminal-20261026.json) failed the mobile
Python source-wiring suite after Android shared tests passed. The source gate
required the separate text `if (current == null)` and rejected the implemented
equivalent null-or-expired branch. This also masked three unrelated mutation
tests behind the same baseline error. Debug assembly, minification and packaged
identity checks were skipped; local compilation did not close those gates.
The missing local source-wiring invocation is recorded rather than treating the
failed immutable run as accepted or retrying it unchanged.

The verifier now scopes its check to `TimedOfferCard`, ignores comments, and
extracts the combined guard's balanced branch. It requires both unavailable and
expired timing, the current countdown read, a refresh flag set before the
callback, and loop exit. New negative cases remove each condition, callback,
loop protection or ordering; a comment decoy cannot satisfy the guard. Equivalent
whitespace is accepted. Existing runtime tests remain the authority for behavior;
this source gate checks wiring rather than claiming to execute Kotlin.

The exact successor checkout's [local evidence](immediate-offer-source-gate-verification-20261026.json)
passes **117 Python source/build-tool tests**,
including all existing mutations and the new guard cases. The earlier baseline
reproduction and working-directory copy observation remain in ignored local
logs. The repair needs its own complete immutable CI, including actual Android
assembly/minification/identity checks. It cannot borrow predecessor results.

The separate city-local time implementation is under local verification in the
main checkout and is excluded from this focused candidate. The existing Trial,
protected rollback data, source-only continuation and physical/provider/staff/
field/public acceptance boundaries remain in force.
