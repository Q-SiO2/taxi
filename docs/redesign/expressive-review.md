# Every-page artwork and motion review

**14 October 2026 — proposed design package; application implementation pending owner confirmation.**

The owner requested every page, unrestricted identity exploration, and a deeper
investigation of graphical decoration and animation. The complete atlas and this
extension address those requests at the design-specification level. They do not
claim that the proposed screens are installed in the app.

## What to open

1. [Full illustrated page atlas](page-atlas.html?art=illustrated): use the complete
   index, search, all-full-compositions mode, or contact sheet. Each of the 213
   views has its own content, controls, states, source anchors and linked specification.
   Switch **Graphic layer** to compare the structural and illustrated versions.
2. [Illustration and motion atelier](expressive-board.html): compare Paper cut,
   Line chronicle and Print studio across five palettes and three type pairings.
   Inspect 24 original vector studies, replay/scrub 18 motion studies, and inspect
   the exact placement decision for any atlas ID. The six integrated journey
   examples demonstrate motion scale; they are not the coverage boundary.
3. [Research](expressive-research.md), [native implementation plan](expressive-motion.md),
   [motion recipes](expressive-recipes.md), [all-page placement ledger](expressive-pages.md),
   and [delivery waves](delivery.md).

## Coverage and evidence

| Requirement | Result | Evidence |
| --- | --- | --- |
| Every documented/source-derived view | 213 unique compositions and 213 standalone specifications: 20 shared, 43 passenger, 40 driver, 9 deferred, 13 applicant, 88 operations | [Coverage and source classification](coverage.md), [page atlas](page-atlas.html), [wave assignment](wave-assignment.md) |
| Check existing application surfaces | 257 named Compose declarations across 54 source files classified as screens, shells, components or helpers; source hashes remain consistent | [Source inventory](source-ui-inventory.json), [source hashes](source-ui-files.json), `verify_atlas.py` |
| Graphical direction for every view | 213 explicit art/motion/slot/size/condition decisions; 181 static illustrated slots and 32 deliberately plain views | [Placement ledger](expressive-pages.md), individual `pages/*.md`, illustrated atlas |
| Original artwork exploration | 24 editable SVG studies with layer anatomy, provenance and hashes; three art languages | [Masters](expressive-assets.json), [atelier](expressive-board.html) |
| Deep external research | 34 unique primary references, observations and applicable design decisions; retrieval limits disclosed | [Research](expressive-research.md) |
| Interesting, controlled animation | All 18 studies exercised through Play, Stop and timeline scrub; bounded cycles and declared native triggers | [Browser record](expressive-browser-check.json), [recipes](expressive-recipes.md) |
| Preserve facts and actions during motion | Six integrated examples checked; displayed facts unchanged; artwork is the animation target | [Browser record](expressive-browser-check.json) |
| Adaptation and control | Reduced-motion and active-driver context suppress motion; pause/visibility controls; all three art directions exercised | [Browser record](expressive-browser-check.json), [native plan](expressive-motion.md) |
| Compact and large-type layouts | Atelier at 320 px with Arabic/Plex/large text and at 1440 px with Jakarta/normal text; no horizontal overflow in checked profiles. Final compact art heights: 140/28/64/40/48/80 px for S02/R05/D10/R18/A04/R33 | [Browser record](expressive-browser-check.json) |
| Complete illustrated compositions | All 213 mounted with 181 art slots; 360 px Arabic/Plex/200% atlas profile checked without horizontal overflow | [Browser record](expressive-browser-check.json) |
| Review-only boundary | Local links, SVG XML/hashes, page coverage, recipe bounds and script syntax pass; specimens contain no service API calls | [Expressive checks](expressive-check.json), `verify_atlas.py` |

Saved views: [direction preview](expressive-preview.png) and
[full artwork/motion board](expressive-full-board.png). The interactive atlas is
the complete page review surface; a screenshot cannot replace its states and index.

## Verification limits

Browser animation and layout checks establish that the review specimens work.
They do not establish Compose rendering, native frame rate, battery consumption,
keyboard/inset behavior, screen-reader acceptance, complete translated copy,
physical-device usability, hosted acceptance, union alpha acceptance or launch
readiness. The Arabic specimen remains draft copy. Timings are proposed values.
SVG studies are code-authored illustrator briefs, not a commissioned final set.
Plain views have an explicit rationale rather than an omitted design decision.

The manual/offscreen stop check exercised stopping while leaving the visible study;
it is not isolated proof of every platform lifecycle transition. Native lifecycle
and interruption checks belong to the implementation acceptance packet.

## Regeneration and implementation handoff

Run from the repository root using Python and Node already available locally:

```text
python docs/redesign/build_expressive.py
python docs/redesign/build_atlas.py
python docs/redesign/build_expressive.py
python docs/redesign/verify_expressive.py
python docs/redesign/verify_atlas.py
python infra/scripts/validate_docs.py
git -c core.whitespace=cr-at-eol diff --check -- docs
```

The second expressive build binds its manifest to the atlas data that now includes
placement decisions. Browser evidence is a recorded manual verification pass and
must be refreshed when relevant layout, drawing or motion behavior changes.

Before application work, record the owner's selected palette, type pairing,
illustration language and motion intensity in the approval record and update the
visual authorities coherently. Use E0–E3 in the native plan within the delivery
waves; retain the independent alpha, controlled-pilot and public-launch gates.
Neither a complete atlas nor selected artwork clears those release gates.
