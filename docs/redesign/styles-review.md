# Four selected styles — completion audit

Recorded 15 October 2026. The owner selected **Folded Streets, Street Press,
Glazed Machine and Notepad**. The identity exploration and documented rollout
are ready for implementation. Native app rollout and release acceptance remain
open; see [ST-1–ST-4](style-options.md#implementation-packets).

## Requirements and evidence

| Requirement | Delivered evidence | Practical limit |
| --- | --- | --- |
| Distinctive styles rather than recolored themes | Four exact choices in the [preview](abstract-lab.html), [atlas](page-atlas.html) and [components](component-gallery.html); separate color-theme proposal withdrawn | Owner preference establishes the direction; worldwide uniqueness is not claimed |
| Abstract movement without the rejected city/taxi hero | Folded Streets uses a spectral field, Street Press uses cut-plane collage, Glazed Machine uses grain and light; four interface contexts each | Browser references establish composition and motion intent, not native rendering cost |
| Quiet Notepad option | Grayscale rules, square structure, meaningful icons and main tasks; decorative field, playback and scrub disabled | Native grayscale tokens and map styling still require implementation; browser filters are specimen shortcuts |
| Every page and shared component | 213 individually authored compositions and standalone specs, all four style profiles, all 40 component specimens; [coverage ledger](style-coverage.md) | Includes documented/deferred surfaces; does not assert 852 new native screens |
| Safe style selection | Browser preference survives reload; atlas style switch retains an entered draft; component payment choice remains selected | Actual app persistence, coordinator ownership and pending requests need native tests |
| Legibility and motion restraint | 16 base token contrast pairs checked; reduced-motion suppression, fixed facts/actions during expressive scrubbing, Notepad guards checked | No claim of complete accessibility certification or device performance acceptance |
| Review beyond a single desktop page | All 213 views and 40 specimens checked in four styles at a 360 px viewport with Arabic draft/200% text; main lab also checked at 320 px with enlarged Arabic | These are browser layout checks; translations, native OS settings, keyboards and physical-device rehearsal remain open |
| Accelerated implementation path | [Selected contract](style-options.md), [delivery waves](delivery.md), roadmap and design authorities agree on ST-0–ST-4 | A-02 remains partial; alpha, pilot and public launch gates remain independent |

The responsive atlas run measured a 345 px document area within the 360 px
viewport, 213 compositions per style and no horizontal overflow. Component runs
measured the same document width, all 40 specimens and no overflow. The main lab
retains nine navigation icons, no main image and four interface contexts.
[Browser evidence](styles-browser-check.json) records these observations and their
limits. The source audit retains 257 named Compose declarations across 54 files
with source hashes checked by the atlas verifier; this work did not implement
native screens.

## Research and rejected directions

[Research](research.md), [animation/art research](expressive-research.md),
[identity reset](identity-reset.md) and [abstract expression](abstract-expression.md)
retain the reference trail, including the BUCK/Rivian exploration. The owner
preferred the interface treatments without the main illustration, then selected
abstract movement and the four named styles. Earlier city/taxi and generated
hero studies remain historical evidence and are absent from the selected preview.
There is no unresolved palette vote or requirement to commission a hero image
before starting the native component proof.

## Reproduce the documentation checks

From the repository root, using the existing Python environment:

```powershell
backend/.venv/Scripts/python.exe docs/redesign/build_atlas.py
backend/.venv/Scripts/python.exe docs/redesign/build_expressive.py
backend/.venv/Scripts/python.exe docs/redesign/build_components.py
backend/.venv/Scripts/python.exe docs/redesign/verify_styles.py
backend/.venv/Scripts/python.exe docs/redesign/verify_abstract.py
backend/.venv/Scripts/python.exe docs/redesign/verify_atlas.py
backend/.venv/Scripts/python.exe docs/redesign/verify_expressive.py
backend/.venv/Scripts/python.exe infra/scripts/validate_docs.py
git -c core.whitespace=cr-at-eol diff --check -- docs
```

Generated checks cover source/specification integrity, local links, script syntax,
selected style contracts and base token contrast. Browser evidence is a separate
observed run, not manufactured by these scripts. App/backend tests, deployment,
real-money operations and phone rehearsal are outside this documentation change.

ST-1 is the next engineering packet: inspect the current theme/storage boundary,
implement the four-value local preference and verify that switching styles retains
ongoing work. ST-2 then proves the actual native components and motion before
the complete view rollout. This sequencing keeps the selected identity intact
while making native acceptance concrete and reviewable.
