# Requirement-by-requirement review packet

**13 October 2026 — planning package prepared; owner approval pending.**
This checks the requested research/design/roadmap deliverable. It does not accept
application functionality, native design, deployment, alpha presentation or launch.

| Requested outcome | Concrete review artifact | Verification / boundary |
| --- | --- | --- |
| Broad taxi UI research | [Research](research.md): first-party mobility references, regional concepts, driver/operations concepts, author Unlumen docs, type/accessibility and form/empty-state patterns | Sources are attributed and historical/concept material is distinguished; borrowed business rules are explicitly excluded. |
| Freedom beyond gold/blue | [Five identities](direction-board.html), [exact tokens](visual-system.md), all selectable in the atlas | Forest, Orchid, Electric, Terracotta and Graphite/Lime are proposals; none is approved or privileged by the old branding. |
| Legible font/color choices | Three bundled licensed Latin/Arabic pairings, [33 contrast checks](contrast.md), enlarged-text/RTL/dark specimens | Static contrast preflight and browser wrapping are preliminary; actual Compose/rendered contrast and translations need acceptance. |
| Unlumen free primitive inspiration | [26 primitive decisions plus additional free catalog references](components.md), [40 component specimens](component-gallery.html) | Original product-specific Compose recreation is planned; no React/Tailwind/Motion dependency or Pro source imported. License/provenance is documented. |
| Every page/dialog individually reviewable | [213 unique full compositions](page-atlas.html); [213 standalone specs and source ledger](coverage.md); six complete contact sheets below | All 213 appear in all-full-compositions mode, with 460 authored sections and 1,010 content/control items. A thumbnail is explicitly a crop; full view/spec contains the rest. |
| Every styled option and relevant state | [Component contracts](components.md), per-page choices/state profiles, palette/type/RTL/scale/state controls | Closed enums and conditional source fields are retained. Record-driven choices are described as authorized-response data, not fabricated. Source conflict/unknown-outcome/privacy rules remain. |
| Checkout-derived completeness | [257 named declarations in 54 files](source-ui-inventory.json), [hashed source files](source-ui-files.json) | Screens, shells, components and helpers are classified separately. No unresolved named screen/dialog/editor candidates in the audited areas. Inline composable lambdas are handled by their parent review; counts are not runtime route coverage. |
| Accelerated alpha and subsequent real-world launch | [Roadmap](../roadmap.md), [UX-0–UX-8 delivery](delivery.md), [complete wave ledger](wave-assignment.md), [navigation/integration](navigation.md) | Full design coverage now; core journey delivery first after approval. Alpha, authorized pilot and public launch retain distinct evidence and ownership gates. |
| Wait before execution | Pending approval in the hub, roadmap and delivery record | Application redesign, device rehearsal and deployment remain stopped; no redesign app code was changed. |

## Every-family contact sheets

These show all individual preview compositions at the 1440 px browser review
breakpoint. Each preview is cropped for the contact sheet; open the named atlas
view for complete content and controls. All displayed data is synthetic.

| Family | Individual views | Saved contact sheet |
| --- | --- | --- |
| Shared mobile | 20 | [All shared views](contact-shared.png) |
| Passenger | 43 | [All passenger views](contact-passenger.png) |
| Driver | 40 | [All driver views](contact-driver.png) |
| Deferred capabilities | 9 | [All deferred views](contact-deferred.png) |
| Applicant | 13 | [All applicant views](contact-applicant.png) |
| Operations | 88 | [All operations views](contact-operations.png) |

## Verification performed

- [Artifact consistency check](artifact-check.json): complete/unique compositions,
  per-spec hashes, source-file hashes, valid references, every ID assigned to a
  wave, 40 component specimens, JavaScript syntax and no API transport in the
  review HTML.
- [Browser check](browser-check.json): all 213 full views mounted, no measured
  horizontal overflow in 320 px/LTR/Jakarta/Graphite/200%, 360 px/RTL/Plex/Orchid
  dark/200%, and 1440 px/FR structural labels/Jakarta/Electric/200% profiles.
  Browser viewport widths exclude scrollbar width in the recorded metrics.
- Inspected map/review and component specimens; verified expired offers disable
  the primary acceptance action. Component gallery also passed its recorded
  desktop RTL/200% overflow check. Saved six family contact sheets and preview.
- Repository documentation validator passed: links, standing blocks, gap/test
  phases and migration head `20260908_0052`. Windows-aware docs whitespace check
  passed; existing Git newline-normalization warnings are not content failures.

FR/AR structural labels are draft previews; narrative content remains English
where not translated. This is not complete localization approval. Native map,
keyboard, safe areas, TalkBack/VoiceOver, physical devices, actual roles/scopes,
hosted journeys and real-world operational acceptance remain the delivery gates.

## Regeneration

Run `build_atlas.py`, `audit_source.py`, `finalize_atlas.py`, `build_atlas.py`
again if the template changed, `build_components.py`, then `verify_atlas.py`
with the repository Python environment. The page books and `atlas_content.py`
are explicit inputs; missing or duplicate compositions fail the build. Browser
screenshots/check records must be refreshed after a material composition change.
The one-time `refine_atlas.py` is authoring history, not part of regeneration.
