# An illustrated world and an authored motion language

**Concept extension, 14 October 2026. Owner confirmation pending.**
The owner asked for graphical decoration and interesting animation after finding
the previous atlas too plain. This extension deliberately broadens the earlier
restrained visual proposal. It supplies actual graphic/motion studies and a
placement decision for every view; it does not change application source.

Open the [visual atelier](expressive-board.html), then the [research](expressive-research.md),
[18 detailed recipes](expressive-recipes.md), [24 editable masters](expressive-assets.json)
and [213-page placement ledger](expressive-pages.md).

The [full atlas with its illustrated study enabled](page-atlas.html?art=illustrated)
now shows the proposed static slot on each of the 181 illustrated views and
retains the 32 intentional plain views. Every standalone page specification
also includes its expressive placement/condition. These are proposed browser
compositions; motion playback remains in the atelier's individually controlled studies.

## The visual idea

TaxiMobile should feel like a place people recognize: a city, a professional taxi,
small objects associated with journeys and a human community. The graphic language
comes from architectural rhythm, the Atlantic horizon, a curved road, a notebook,
a keyring, a folio and a journey ticket. These elements can give the app character
without turning every page into a scene or treating a decorative graphic as data.

The board compares three coherent directions independently of the five palettes:

| Direction | Drawing and composition | Best applications | What to evaluate |
| --- | --- | --- | --- |
| **Paper cut** | Bold silhouettes, a few overlapping planes, a warm accent and crisp outline; city/taxi foreground, sun and background have separate layers | Welcome, idle driver, onboarding, true-empty history | Friendly enough for passengers, professional enough for drivers/union; avoid a toy-like vehicle or too much illustration height |
| **Line chronicle** | Architectural outlines, sparse colored planes, large negative space; same object proportions as the solid family | City/account headers, vehicles, documents, console empty states | Distinctive editorial feel, small-scale readability and coherent stroke weights; thin detail cannot become faint on a phone |
| **Print studio** | Ticket cuts, controlled rotation, interleaved road bands and sparse halftone texture; graphic composition rather than wallpaper | Receipts/trip history, welcome chapter cards, presentation material, administrative header crops | Expressive without competing with fare/status/table text; distinguish decorative seal/sunburst from verified credentials |

Initial recommendation for comparison: **Paper cut** as the main illustration
family, using the ticket/route motifs as a related graphic finish. **Line chronicle**
is a strong alternative for a more editorial professional character. **Print studio**
is the most expressive experiment. No direction or palette is adopted. Review
Forest, Orchid, Electric, Terracotta and Graphite/Lime without privileging the old
gold/blue look. Existing licensed interface icons remain a separate consistent
family; decorative illustrations are not new unlabeled navigation icons.

## Graphic vocabulary and precise scale

| Motifs | Anatomy | Placement and scale |
| --- | --- | --- |
| G01 city layers / G02 taxi / G03 city linework | Rounded body, distinct wheels/windows/light; simple stacked architectural forms; sun/road separate | 160–220 dp dedicated welcome area, 96 dp idle-driver area, 32–64 dp chapter crop; collapse before crowding controls |
| G04 route ribbon / G17 stop rhythm / G21 weave | A curved band, anchored shapes and repeated rhythm | Abstract header emblem 24–40 dp; console edge 16–24 dp. Actual map geometry/stop labels remain separate data. |
| G05 ticket / G11 notebook | Perforated margins, blank page layers, small line accents | Receipt rim 12 dp outside text, 48 dp header emblem, 96–128 dp true-empty history object |
| G06 sunburst / G07 arch / G08 tile / G09 wave / G22 print | Large geometric rhythm with deliberate whitespace | Static corners or cropped header accents; one focal ornament per page. Texture never underneath body text or map controls. |
| G10 keyring / G20 vehicle blueprint / G23 day-night | Recognizable professional objects with limited perspective | Driver/account/vehicle headers 32–96 dp; actual vehicle identity and display preference stay labelled |
| G12 folio / G15 calendar / G18 envelope / G19 security | Two or three layers, clear silhouette, sparse internal marks | Step/rationale/true-empty art 80–112 dp, compact populated-view emblem 24–64 dp |
| G13 people / G14 helpful object / G16 compass | Abstract people/object expression, no real-person likeness or credentials | General help/onboarding 80–112 dp; small point/rationale emblem where appropriate |
| G24 small spark | Check-shaped graphic and four rays | 56–80 dp suitable confirmed acknowledgement; no completed-but-unpaid celebration |

Every master uses a 320×240 viewBox and separate `data-layer` groups. The original
code-authored studies are editable briefs for an illustrator to refine. They are
not presented as a commissioned human illustration set. The manifest records
original provenance and hashes. No reference-brand artwork, character, logo or
photograph is copied. Existing app assets/provenance are preserved.

At 200% text, forms and instructions get space first: shorten/collapse/remove the
art slot, retain the same object rest pose, and keep the action footer reachable.
Arabic text is real text using the selected Arabic family, outside the illustration;
do not bake labels into SVGs, reveal glyphs individually or mirror cars/maps as
though they were navigation arrows. Decorative material is hidden from assistive
reading unless it communicates additional necessary meaning.

## Motion has a recognizable character

Use an authored performance rather than a generic bounce on every object:
the taxi rolls into its frame and parks; the skyline assembles; a ticket opens;
a folio fans; a notebook tilts; coastal strokes drift; a Help object winks once.
Each study has its own duration, affected layer, trigger, interrupted pose and
native recipe in [expressive-recipes.md](expressive-recipes.md).

| Tier | Proposed timing | Behavior |
| --- | --- | --- |
| Immediate interaction | 100–180 ms | Press/tone/contained object compression; target and label remain stable |
| Interface continuity | 220–300 ms | Panel/selection transitions; actual selected record and focus survive |
| Illustration entrance | 420–820 ms | One localized performance on entry; content/action is available immediately |
| Welcome story | Up to 1100 ms | Car/layer sequence in a reserved artwork frame; never an artificial startup delay |
| Ambient artwork | 1400–2400 ms per cycle, at most three cycles | User-controllable or context-eligible; stops when offscreen/hidden/context changes; static after completion |

The board uses a proposed decelerating curve `cubic-bezier(0.22,1,0.36,1)` for most
studies, linear progression for an indeterminate band and gentle ease-in-out for
waves. These are starting values, not a claim of identical browser/Compose feel.
Native spring experiments should bound decorative scale near 1.03, settle within
the recipe duration and never overshoot a functional target. Arbitrary path
morphing requires aligned authored geometry or a separately justified tool;
simple transforms/trimmed paths already provide most of the desired character.

Motion intensity follows context. Welcome, idle account/onboarding and general
Help can be expressive. An active driver job, money review, authentication proof,
protected document and incident narrative uses a stable task surface. This is
an assignment decision in the [every-page ledger](expressive-pages.md), not a reason
to leave the whole application visually plain. Thirty-two views intentionally
receive no decorative artwork; 181 receive a slot, and 38 have a named optional
motion recipe. Shared focus/press feedback is additional, not counted as a new
illustration animation on every screen.

## Specific outcomes are never suggested by decoration

R17/D20/D21/D22 use ticket/ledger framing while cash is pending. Opening a receipt
may reveal its illustrative rim, but the fare and status are already readable.
A separate suitable server-confirmed acknowledgement can use G24/M12. A submitted
manual transfer, scan in progress, uploaded file or driver commitment does not
produce that acknowledgement. Real route display uses real route geometry; the
abstract route ribbon is a brand emblem. Waiting motion is explicitly
indeterminate and stops on completion/failure, not an invented dispatch story.

## Unlumen refinements

Revisit Clipped Circle as the author actually implements it: a pointer-following
spotlight. The earlier circular-crop description was imprecise. The native proposal
is an illustration-only light sweep with a tap/focus/replay alternative and static
touch fallback. Highlight supplies the idea of a smoothly traveling selection wash;
Progressive Blur supplies an edge treatment to compare against cheaper opaque/scrim
layers. The optional tilt experiment belongs to an artwork preview, not to Accept,
cash confirmation or a map hit region. Free primitive provenance/license boundaries
remain documented in [the research](expressive-research.md). No React, Motion,
Tailwind, Rive or Lottie dependency was added to the app.

## Native implementation path after approval

Current source inspection confirms that optional artwork is loaded through
`feature/ui/components/OptionalArtwork.kt` as bounded local PNG data with a painter
fallback. It explicitly treats art as optional. Do not pass these SVG documentation
masters directly to Android resource decoding and repeat the earlier asset failure.

| Need | Proposed first implementation | Evidence needed |
| --- | --- | --- |
| Static illustrated objects | Reviewed PNG export at the required densities through existing bounded optional-art loader, or cached Canvas/Path geometry | Actual Android/iOS/web render, missing/corrupt-art fallback and no impact on task content |
| Simple layered motion | Cached Canvas paths + Animatable / Transition / graphicsLayer; layer transforms separate from layout and hitboxes | Native rest/active/interrupted/reduced poses and frame-time observations on representative hardware |
| Illustration/path draw | Cached path geometry and trimmed segment/dash offset; diagram text rendered normally | Actual path direction/line width under scale/RTL; no route-data substitution |
| Stateful illustration | A small explicit presentation state, keyed to the actual UI event; cancellation in session/scope/lifecycle teardown | No replay from stale callbacks, no post-sign-out animation/state restoration |
| Advanced polygon morph | Separate proof with the documented `graphics-shapes` dependency if a selected concept needs it | Compatibility/value assessment; no automatic dependency addition |
| Designer-authored character film | Compare a local exported sequence with Rive/Lottie only if selected artwork genuinely exceeds the simple path/layer approach | Android/iOS/JS/Wasm integration, payload/renderer/lifecycle/accessibility and artist licensing; no blanket KMP support assumption |

The selected asset's dimensions and parsed paths are cached; animation changes
progress/transform only, not asset decoding every frame. Keep decorative rendering
outside operational map measurement, offer command gates and payment state.
Bound concurrent scenes: one illustrative scene on a native mobile page, not
all 18 board studies in production. Stop on hidden/offscreen state, app background,
role/scope/session change or active-driver context. The static rest pose remains.

## Delivery addition to the alpha roadmap

This enriches UX-0/UX-1 and existing page waves rather than introducing a second
rewrite. Approval chooses art language, identity/type and motion intensity together.

| Slice | Concrete output after approval | Suggested focused days / exit evidence |
| --- | --- | --- |
| E-0 Select/refine the family | Choose one of the three directions; illustrator review of taxi/city/key/document/ticket proportions; finalize small/hero/static assets and notices | 1–2; reviewed contact sheet and precise approved asset revision |
| E-1 Native motion foundation | Shared scene tokens, cached artwork layers, static/reduced/hidden lifecycle and fixed action regions | 1–2; actual platform study packet with interrupted poses |
| E-2 Core expression | S02 welcome, D10 idle driver, R05 journey emblem, R18 receipt framing, A04 onboarding and R33 Help | 2–4; actual screens with terms/status/actions readable; no invented data/state |
| E-3 Secondary placement | Apply the complete placement ledger while each already planned page wave is implemented | 1–3 incremental; no independent feature rewrite; all alpha-reachable views reviewed |

The **5–11 focused-day** range is provisional and incremental to the prior plan;
some scene/foundation work overlaps UX-1. Do not blindly add or subtract it from
the 4–8 week alpha target. Prioritize one polished scene/object family and the
selected finite motions, then expand through the same vocabulary. Unselected
experiments remain in documentation. No launch date or native performance result
is inferred from a browser animation.

## Review and acceptance

The [board](expressive-board.html) exposes all studies, art directions, five
palettes, type pairings, reduced motion, active-work suppression, RTL, enlarged
text and all 213 placement decisions. The six integrated screen specimens are
placement examples; the complete existing page atlas and every-page ledger
remain the coverage source.

Before calling an implemented slice accepted, retain real static/start/mid/end/
interrupted/reduced frames, long French/Arabic text, 320/360/430 dp, keyboard/insets,
assistive reading, outdoor/night samples and the existing role journeys. Measure
actual frame behavior/payload on a lower-end target and with maps visible; browser
smoothness is not native performance. Verify that artwork failure leaves the
task usable, all async completion callbacks respect the current session/context,
and consequential labels never animate into a false success state.

**Owner selection record:** pending. Art language: —. Identity/type: —. Motion
intensity: —. Selected studies: —. Approved asset revision: —. Native packet: —.
