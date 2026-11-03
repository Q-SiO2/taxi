# Research, visual references and design decisions

**Proposed — researched 12 October 2026.** Links were inspected through live
search, page content and selected browser/image views. Product websites are
reference evidence, not a claim that every market/version has the same app.
Historical redesign articles are labelled below. Concept work is attributed to
its creator and is composition inspiration, not validated usability research.
Original artwork, proprietary fonts and source code are not copied into the app.

## What the current render tells us

The unobstructed physical passenger map shows an oversized floating name capsule,
separate safety/inbox capsules, two raised map controls, a large headline and two
full-width buttons. The name truncates while substantial chrome occupies the map.
The primary action says “Find a place” even though the chosen alpha is map-only.
These are observed facts from the retained render, not a universal diagnosis of
every current screen. Account/history/support, booking and trip states currently
share large passenger/driver source files and map-sheet panels.

Current source already selects Noto Sans Arabic centrally for Arabic Material
typography; the older audit's missing-integration finding is therefore historical.
Gold body text on white is prohibited in current docs and the primary gold button
uses dark text. A redesign still needs fresh contrast checks for every actual
foreground/background pair, rather than repeating an old audit as current fact.

The design response is structural: fewer persistent controls, bounded typography,
explicit navigation, one task per page, a stable action region and truthful states.
The owner's rejection is the strongest evidence that the current aesthetic is
unaccepted. No invented passenger interview or measured conversion improvement
is used to justify the new proposal.

## Mobility products: transferable patterns and limits

| Reference | Evidence inspected | Design lesson proposed for TaxiMobile | Boundary |
| --- | --- | --- | --- |
| [Uber Base](https://base.uber.com/) | Current official foundations/components hub | A small coherent vocabulary used across roles; strong hierarchy | Proprietary brand/typefaces are not ours; hub does not prove TaxiMobile usability. |
| [Uber rider](https://www.uber.com/us/en/ride/) | Current official destination/ride presentation | Make the journey and next action dominant | No copied service catalogue, promotions or live-supply promises. |
| [Uber rider rebuild](https://www.uber.com/us/en/blog/new-rider-app-architecture/) | 2016 engineering account | Treat booking as a cohesive journey rather than adding isolated screens | Historical architecture article; does not justify replacing KMP. |
| [Uber driver rebuild](https://www.uber.com/in/en/blog/driver-app-ribs-architecture/) | 2018 engineering/design account | Driver workflows deserve their own hierarchy and user research | Historical; source architecture is not a migration recommendation. |
| [Bolt Rides](https://bolt.eu/en/rides/) | Current official product and fare explanation | Compact trip choice; distinguish estimate from final payment | TaxiMobile only exposes city-authorized services. |
| [Bolt driver guide](https://bolt.eu/en-py/driver/guide/driver-rating/) | Pickup, identity and trip-completion guidance | Put exact pickup and vehicle identity where the user needs them | Masked calls/PIN cannot be assumed available in TaxiMobile. |
| [Lyft rider redesign](https://eng.lyft.com/meet-sravanthi-one-of-the-pms-behind-lyfts-new-rider-app-9bc61abeee31) | 2019 first-party research account | Validate discoverability with tasks and support evidence | Historical; no importing shared-ride business rules. |
| [Lyft Maps](https://www.lyft.com/blog/posts/lyfts-secret-plan-to-take-control-of-its-maps-and-its-future) | 2023 first-party map account | Map labeling and pickup clarity are product design work | We keep MapLibre and existing routing contracts. |
| [Careem booking](https://help.careem.com/hc/en-us/articles/360001583548-How-to-book-a-ride-from-Careem-app) | Official flow and screenshot/animation references | Clear pickup, destination, method, fare and confirmation progression | No super-app home, OTP promise or unsupported car categories. |
| [Careem ride standards](https://help.careem.com/hc/en-us/articles/1500010067702-What-are-Rides) | Pickup-detail and rating examples | Use practical entrance/landmark language in coordination | Text notes only where our API supports them. |
| [Careem captain](https://drive.careem.com/) | Current first-party onboarding entry | Make eligibility and application status distinct from account creation | Our approval remains city/operator-scoped. |
| [Freenow booking](https://support.free-now.com/hc/en-gb/articles/360020681173-Booking-Managing-Your-Trip-request) | Official pickup adjustment and accepted-driver flow | Confirm the pickup pin and show identity after acceptance | Do not expose pre-assignment supply or import foreign meter policy. |
| [Freenow services](https://www.free-now.com/ride-hailing/ride/) | Official service presentation | Explain service differences in concise labelled rows | Show only actual city capabilities. |
| [G7 account](https://aide.g7.fr/hc/fr/articles/7438969244316-Comment-t%C3%A9l%C3%A9charger-l-application-G7-et-cr%C3%A9er-un-compte) | Official distinction between public and subscriber apps | Clear product role and professional-taxi identity | No confusing passenger/driver role toggle after login. |
| [G7 redesign](https://www.g7.fr/uploads/files/cp-g7xnouvelle-application.pdf) | Historical first-party release material | Study licensed-taxi presentation and reduced booking friction | Historical product announcement, not current screen truth. |
| [Curb rider](https://rider.gocurb.com/) | Current official request/schedule/receipt presentation; browser view | Professional taxi positioning; clear now/later distinction | Pair-and-pay and emailed receipts are not automatically in scope. |
| [Curb driver](https://www.gocurb.com/driver-app-support) | Current official licensed-driver support | Driver tools fit professional work and existing taxi practices | Do not imply cross-dispatch integration. |
| [Cabify safety](https://cabify.com/en/riders/safety) | Official shield placement and identity/vehicle presentation | Safety action remains discoverable without taking over the booking UI | No invented phone masking, live sharing or emergency dispatch. |
| [Cabify accessibility](https://cabify.com/en/riders/accessibility) | Official contrast and accessible-control rationale | Homogeneous controls; safety and help remain readable | Accessibility service preferences require a separate product contract. |
| [Grab navigation](https://www.grab.com/my/bottom-navigation/) | Official service/menu redesign | Label navigation and limit competing tasks | No pre-assignment arrival predictions or super-app advertising. |
| [Grab scheduling](https://www.grab.com/inside-grab/stories/advance-booking-schedule-rides/) | 2024 first-party scheduling problem analysis | Received/committed/unfulfilled bookings must be distinguishable | We do not copy its reliability guarantees. |
| [Grab pickup tips](https://www.grab.com/inside-grab/stories/book-grab-rides-product-feature-tips/) | First-party pickup/booking reference | Keep meaningful recent destinations close to booking | Saved widgets and persistent Home/Work are later capabilities. |
| [Gett rider help](https://www.gett.com/uk/help/riders) | Current first-party pin/search/now-later flow | Confirmation panel combines journey and relevant terms | TaxiMobile fare policy remains local and server-owned. |
| [taxi.eu](https://www.taxi.eu/) | Current first-party journey and professional-taxi presentation | One identity across cities with city-specific capability | No claim that foreign payment networks operate here. |
| [inDrive passenger guide](https://blog.indrive.com/en-in/article/passengers-101-how-to-use-our-app) | First-party guide discovered and inspected | Strong locality and direct next-action language | Fare bidding and passenger driver selection conflict with our model. |
| [DiDi help](https://web.didiglobal.com/au/help-center/can-i-pre-book-a-trip/) | Current official market-specific capability explanation | Omit unavailable functionality instead of simulating it | Scheduling availability differs by market; our server decides. |
| [Kakao T taxi](https://www.kakaomobility.com/service-kakaot/taxi) | Current official service presentation | Service identity and a complete booking-to-payment story | No super-app service expansion. |
| [Kakao T redesign](https://www.kakaomobility.com/newsroom/detail/%EC%B9%B4%EC%B9%B4%EC%98%A4%EB%AA%A8%EB%B9%8C%EB%A6%AC%ED%8B%B0-%EC%B9%B4%EC%B9%B4%EC%98%A4-T-%EC%95%B1-%EC%82%AC%EC%9A%A9%EC%84%B1-%EC%A0%9C%EA%B3%A0-%EB%8D%94-%EC%89%BD%EA%B3%A0-%EC%A7%81%EA%B4%80%EC%A0%81%EC%9D%B8-%EC%9D%B4%EB%8F%99-%EA%B2%BD%ED%97%98-%EC%A0%9C%EA%B3%B5--330) | 2025 first-party navigation announcement | Organize by user intent rather than listing every feature | Personalized recommendations need data/product approval. |
| [Heetch](https://www.heetch.com/?lang=en) | Current first-party positioning, French-language identity | A distinct visual personality can coexist with straightforward booking | No copied brand or claims about commissions/service coverage. |

## Experimental composition references

| Creator and link | What to explore | What to discard |
| --- | --- | --- |
| [Ronas IT / Dmitry Lauretsky](https://dribbble.com/shots/23691282-Taxi-Booking-App-Design) | Visually inspected two-phone image: bounded booking sheet, tidy journey rows and compact driver identity | Luxury vehicle imagery, tiny labels, payment/card controls and speculative ETA. |
| [Ronas IT taxi concept](https://dribbble.com/shots/24948188-Taxi-Booking-App) | Strong welcome hierarchy and booking progression | Sports-car hero and aspirational claims that misrepresent licensed taxis. |
| [Abdullah Al Mamun booking/payment](https://dribbble.com/shots/26083550-Taxi-Booking-App-Booking-Payment-Page-UI) | Trip and fare composition | Unavailable checkout features and untested tiny-screen density. |
| [Rachid Benaissaoui iRcab](https://www.behance.net/gallery/149832175/iRcab-App-UXUI-Case-Study) | Regional French-language taxi context and coherent journey concept | Claimed offline booking; TaxiMobile requires authoritative connectivity. |
| [Khalil Ur Rehman iTAXI](https://www.behance.net/gallery/151295187/iTAXI-Taxi-Booking-App) | Image-search reference: route/identity grouping and restrained green | “Taxi on its way” before our backend confirms it. Gallery fetch unavailable. |
| [Roohi Koohi](https://dribbble.com/shots/20716610-Taxi-Mobile-App-Ui-Design) | Image-search reference: sparse location rows and white-space rhythm | Exotic vehicle choice and unsupported chat/call controls. |
| [JK Mahbub RideCap](https://dribbble.com/shots/26387944-RideCap-Smooth-Taxi-App-UI-Animation) | Image-search reference: controlled active-state transitions | Futuristic effects and hourly rentals not in our model. |
| [Evgenia Ornatskaya](https://www.behance.net/gallery/185038763/Mobile-app-TAXI-BOOKING) | Image-search reference: route summary above service choices | Dynamic-price theatre and imaginary service assortment. |
| [Comfygen concept](https://dribbble.com/shots/27055711-Taxi-Booking-App-UI-UX-Design-Smart-Seamless-Ride-Experience) | Image-search reference: connected location fields and panel rhythm | Social login, persistent Home/Office and unsupported stops. |
| [TaxiGo](https://www.behance.net/gallery/192557297/TaxiGo-Online-Taxi-Booking-App-Design) | Image-search reference: welcoming destination entry | Visible nearby-cab counts directly violate supply privacy. |

These are a breadth sample, not a leaderboard. A convincing mockup is not proof
that its text remains readable at 320 dp, in Arabic or in outdoor driver use.
The board's new compositions are original and do not reproduce these images.

## Unlumen: verified source and selective use

[unlumen.com](https://unlumen.com/) currently redirects to
[ui.unlumen.com](https://ui.unlumen.com/). Its Primitives link resolves to
[the author docs](https://unlumen-ui-docs.vercel.app/docs/ui); the public
[repository](https://github.com/leovvx/unlumen-ui-docs) identifies the docs and
registry. The [license](https://unlumen-ui-docs.vercel.app/docs/license) permits
commercial product use and adaptation of free components, but restricts
redistribution as a component library/registry and requires a license for Pro.
Free is not equivalent to MIT. We will implement original Compose behaviors
in the product, retain provenance, and check component-specific terms before
adapting any source. No registry package or purchased Pro element is needed.

The [catalogue](https://ui.unlumen.com/components) marks Dock, Sidebar 001,
Animated List and Motion FAQs Accordion free. AI Chat and Motion Tabs Menu are
currently Pro; no assumption that an old badge grants access is carried forward.
Use [Highlight](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/highlight)
for the feel of a moving selection wash;
[Shimmer Skeleton](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/shimmer-skeleton)
for shaped loading;
[Copy](https://unlumen-ui-docs.vercel.app/docs/ui/buttons/copy) and
[Refresh](https://unlumen-ui-docs.vercel.app/docs/ui/buttons/refresh)
for contained feedback;
[Switch](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/switch)
for settings, not instant driver availability;
[Command Menu](https://unlumen-ui-docs.vercel.app/docs/ui/unlumen/command-menu)
for optional operations navigation. These observations inform our own specs.
The full treatment of all 28 listed primitives is in [components.md](components.md).

## Type and accessibility sources

[Inter](https://rsms.me/inter/) offers text/display optical sizes and tabular
numbers, under OFL. [Plus Jakarta Sans license](https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/OFL.txt),
[Noto Sans Arabic license](https://github.com/google/fonts/blob/main/ofl/notosansarabic/OFL.txt),
and [IBM Plex](https://www.ibm.com/design/language/typography/typeface/)
with its [OFL](https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt)
support the proposed specimens. Bundle reviewed files and their notices; do not
depend on external font requests in the eventual product. Inter is proposed in
explicit conflict with the old UI prohibition; owner approval resolves that rule.

Use W3C's [contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html),
[target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html),
[motion guidance](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)
and [bidirectional-text guidance](https://www.w3.org/International/articles/inline-bidi-markup/).
Our proposed 48 dp native targets are a product choice above the web minimum,
not a claim that WCAG specifies Android dp. Static contrast calculations and
browser specimens are preliminary; actual Compose/device accessibility remains
required after implementation.

## Decisions supported by the research

### Additional research for secondary pages — 13 October

The owner rejected representative-screen coverage. These references support the
new account/forms/console compositions; they supplement the mobility research
above. They do not prescribe TaxiMobile business rules.

| Reference | Observation and proposed application | Boundary |
| --- | --- | --- |
| [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/) | Ask only needed questions, explain optional fields and provide an understandable return path. Apply task grouping to credential, vehicle and policy forms. | We retain the existing API fields and validation; splitting a view does not change request semantics. |
| [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/) | Review relevant entered facts before submission. Apply exact-target summaries to application, authorization, cash and lifecycle dialogs. | Review cannot bypass independent approval or MFA; actual outcomes remain server-owned. |
| [GOV.UK validation](https://design-system.service.gov.uk/patterns/validation/) | Make field errors recoverable with an error summary and local explanation. | Keep safe drafts only; secret recovery fields are cleared according to the actual auth contract. |
| [GOV.UK focus states](https://design-system.service.gov.uk/get-started/focus-states/) | Visible keyboard focus is part of the component treatment, including low-information icon actions. | Actual Compose/browser keyboard and assistive checks remain required. |
| [Carbon empty states](https://www.carbondesignsystem.com/building-blocks/core/patterns/empty-states) | Use an explanation and useful action appropriate to why content is absent. | Empty, failed, restricted, suppressed and filtered results stay distinct; zero records never implies operational readiness. |
| [Ronas IT driver dashboard concept](https://dribbble.com/shots/27666535-Taxi-Dashboard-Logistics-Driver-App) | Contrast professional driver information hierarchy, route context and dark surfaces with passenger booking. | Concept, not an accepted product; no pressure incentives, unsupported speed data or swipe-only confirmation. |
| [Arunav Rahul fleet dashboard concept](https://dribbble.com/shots/25504560-Action-Taxi-Taxi-Fleet-Management-Dashboard) | Explore purposeful queue/detail density and explicit administrative context. | No copied private driver trails, automatic ranking or commercial fleet rules. |

These findings led to separate compositions for sessions, password/recovery,
driver preferences/membership/credentials, selected city detail, exact readiness
review, refund evidence, restricted case actions and the full policy editors.
The [source audit](coverage.md) ties those views to current source declarations.

### Synthesis for the complete atlas

All 213 views use the same chosen type/color/geometry system, but retain their own
task anatomy: authentication forms, map selection, journey review, timed offers,
cash recovery, receipts, document slots, timelines, queues, editors, review
dialogs and restricted gates. This is a design synthesis from the references and
current TaxiMobile contracts, not a claim that a reference app has these exact
features. Five identities and three font pairings can be compared on every view.

The browser atlas supplies original schematic layouts and synthetic values.
Long FR/AR copy, actual native map rendering, physical driver interaction and
translation quality need the platform acceptance work specified in delivery.md.

- Make core booking more focused than a multi-service commercial super-app.
- Treat a taxi driver as a professional operator; keep offers and current work
  readable and avoid incentives, gamification or acceptance-pressure decoration.
- Use a coherent visual language across public and protected surfaces, with
  desktop density rather than enlarging mobile cards into an admin dashboard.
- Design Arabic as a first-class composition, including mixed-script identifiers,
  wrapping, mirrored chrome and font metrics.
- Spend visual novelty on color, type, composition and restrained selection
  motion. Do not make prices, emergency information or critical tap targets move.
- Test pickup, fare understanding, matching uncertainty and cash recovery as
  explicit tasks. Research references cannot replace TaxiMobile usability evidence.
