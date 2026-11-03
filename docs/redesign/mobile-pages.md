# Complete passenger and driver page book

**Proposed — implementation waits for owner confirmation.** Screen IDs specify
surfaces and states, not permission to add unsupported capabilities. Component
IDs refer to [components.md](components.md); every color/type/size uses
[visual-system.md](visual-system.md). This page book replaces map-sheet panel
accumulation with task-focused compositions while preserving coordinator/domain
contracts. Navigation structure itself is an owner-review choice.

## Navigation, state and styling contract for every page

Passenger idle navigation: **Ride / Trips / Account**. Trips contains Past and
Upcoming when scheduling is enabled. Account contains Profile, Inbox, Help,
Language and Sign out. Safety is directly reachable on an assigned ride. Driver
idle navigation: **Work / Earnings / Account**; Work includes Upcoming where
enabled, Account contains Vehicles, Application status, Inbox, Help and settings.
Active work takes over the map/action region, with an explicit way to return
after viewing permitted details. Navigation never cancels work or fabricates state.

Every page inherits these acceptance/state profiles:

| Profile | Required presentation and behavior |
| --- | --- |
| G — global | EN/FR/AR, 320/360/430 dp, 1×/1.3×/1.6×/2× text, safe areas, RTL, reduced motion, focus/assistive labels, stable action reachability; long labels wrap |
| F — form | Default/focused/filled/invalid/busy/conflict/rate-limited/offline/unknown outcome; persistent labels; one write in flight; safe draft preserved; no duplicate submission |
| R — read | Loading/empty/loaded/error/stale/restricted/expired session; failed read is not empty; unauthorized details removed; refresh restores server facts |
| M — map | Location unknown/denied/stale, tiles loading/failed, outside area, no provider, keyboard/sheet overlap, accessible non-map summary; attribution retained |
| J — journey | Server lifecycle, cancellation pending/conflict, recovery after restart, assigned identity absent, stale route/location; no inferred progression |
| W — financial | Estimate/final unavailable, cash pending/completed, transfer pending/processing/completed, partial/full refund, uncertain command; no local success inference |

The final column below names additional edge cases, not the whole state contract.
All pages inherit G and the listed profiles. Stable buttons, type scale, markers,
badges, lists, sheets and fields are completely specified in the component book;
there is no per-page font, radius, gradient or button invention.

## Shared startup, authentication and permissions

Source: shared `App.kt`, `feature/app/TaxiMobileScreen.kt`, `AppUiState.kt`,
`MobileAppCoordinator.kt`, `feature/auth/AuthenticationSessionCoordinator.kt`;
native permission/requester implementations stay platform-specific.

| ID / page | Layout and visual hierarchy | Fields/options and next actions | Profiles / specific acceptance |
| --- | --- | --- | --- |
| S00 Session restore | Solid neutral surface, small mark, one line “Checking your account”, contained indicator; no full-screen dark branding delay | No artificial timer; navigate on real restoration/compatibility result | R; valid session returns to current trip, not idle; slow restore provides honest status |
| S01 Compatibility gate | Page title, concise update/unsupported explanation, version detail secondary, fixed action | Retry check; approved update destination if available; no fake download button | R; API failure differs from unsupported client; bypass never offered |
| S02 Welcome | Compact original illustration, two-line role-specific introduction, language selector, one primary sign-in and secondary create account | Passenger and driver install identities clear; no role-switch tab; no social-login icons | G; no oversize title or artwork; language available before auth |
| S03 Sign in | Page bar, identifier field, password field, recovery link, stable primary footer; no map background | Email/Moroccan phone + password; reveal password; Sign in; Create account | F; preserve identifier, never persist/log password; role mismatch, throttle and offline explicit |
| S04 Create account | Short stacked form, inline input guidance, readable password rule; compact title | Supported name/contact/password fields; create role-specific account; Back to sign in | F; repeat backend shape constraints; no OTP/verified-contact implication; successful create returns to sign-in |
| S05 Account-created acknowledgement | Static check, “Account created”, brief next step; same form scale | Sign in with prefilled identifier; no auto-authenticated account claim | R; secrets cleared; login remains a real action |
| S06 Recovery | Plain labelled form, neutral privacy-preserving explanation, one submit | Identifier, saved recovery code, new password; reveal new password; Back | F; generic accepted response prevents account/code enumeration; no email-reset promise |
| S07 Recovery acknowledgement | Small status symbol, conditional explanation, clear return | Return to sign in; never echo code/password or assert which account existed | R; source response semantics preserved |
| S08 Session expired / revoked | Inline notice or focused auth handoff, safe context label; no repeated red modal | Sign in; safe Back; clear secure credentials when required | R/J; stale session callbacks cannot restore prior identity; no unsafe command replay |
| S09 Connection interruption | Compact health strip over last confirmed page, expanded offline detail when requested | Retry / connection guidance; read permitted cached facts; unsafe writes disabled | R/J; no full-page offline dead end over an active trip; last refresh visibly aged |
| S10 Location rationale | Small location icon, human explanation of why/when, context-specific CTA | Continue invokes native permission; Not now for passenger; settings guide after permanent denial | M; no fake OS prompt; driver online blocked with explanation if required observation unavailable |
| S11 Notification rationale | Compact text, useful examples, permission action and Not now | Request native permission only at relevant moment; app remains usable without it | G; no forced startup prompt or claim that push changes authoritative state |
| S12 Language / style | Three labelled languages and four checked style rows with compact previews | English / Français / العربية; Folded Streets / Street Press / Glazed Machine / Notepad | F; local preference; preserve task/draft; OS reduced motion; Notepad always disables decorative motion |
| S13 Sign-out confirmation | Compact review where necessary, account name and local-clearing explanation | Sign out / Cancel; connected revocation attempt with documented local clearing | F/J; sign-out works offline and fences subsequent restoration |
| S14 Account security | Dedicated sessions/password/recovery navigation, current-security read state | Sessions; Change password; Generate recovery codes; reload | R/F; already supported, not a deferred capability; no secret stored in navigation |
| S15 Password change | Two labelled password fields and explicit consequence warning, separate fixed submit | Current password; new password (12-character minimum); reveal; submit | F; no new confirmation field/API assumption; server outcome/credential clearing governs next state |
| S16 Active sessions | Device label/current-session marker, created/expiry dates, revoke action per row | Review revocation; refresh; current-session action explicitly says sign out | R/F; failed list read not zero sessions; exact session ID stays internal |
| S17 Session revocation review | Selected device and current/other-session consequence in destructive review | Revoke or sign out this session; Cancel | F; server-owned effect; no raw token exposure; no uncertain write replay |
| S18 Recovery-code generation | Current-password field, replacement warning and concise custody instructions | Generate new codes; reveal password; Back | F; account-password proof required; no generated code before actual server response |
| S19 One-time recovery-code custody | Legible isolated secret rows, actual expiry, acknowledgement checkbox, clear-after-save action | Acknowledge saved; clear in-memory display | R/F; only synthetic placeholders in design artifact; real codes never logged, captured in evidence or persisted as UI draft |

## Passenger booking: a composed journey

Source: `feature/passenger/PassengerHome.kt`, passenger form/presentation models,
`feature/maps`, `feature/places` and current coordinator/gateway contracts.
Do not split business authority into new screen-owned state machines.

| ID / page | Layout and visual hierarchy | Fields/options and next actions | Profiles / specific acceptance |
| --- | --- | --- | --- |
| R00 Ride home | Quiet map, city label, one 48 dp account entry if global nav is not visible; content-sized bottom panel “Your next trip”; labelled bottom nav | Primary “Choose destination on map”; Fixed routes as compact secondary row; Now/Later only where scheduling enabled | M/R; map-only alpha has no search launcher; no taxi dots/counts; idle header never displays truncated full name |
| R01 Destination map | Page bar “Choose destination”, fixed B-pin, point summary and stable footer; no competing account bar | Move map; recenter; Confirm destination; Back restores draft | M/F; selection is not a geocoded address; inaccessible map has approved fallback |
| R02 Pickup map | Same anatomy with A-pin, location accuracy guidance when known, clear pickup instruction | Move map; use fresh current location; Confirm pickup; Edit destination | M/F; never silently use last device location as confirmed pickup; boundary errors actionable |
| R03 Point confirmation / fallback | Two linked A/B rows with clear human labels, compact map preview, location limitations inline | Edit either point; approved coordinate diagnostic only in development; Back | M/F; no raw coordinate form in primary consumer UI; no invented landmark name |
| R04 Optional place lookup | Later provider-enabled dedicated page with one search field, recent authorized results and attribution | Debounced query; result selection; explicit Retry; Choose on map always reachable | M/R/F; hidden in alpha; no result/address invention, query/rate-limit/error preserved |
| R05 Ride review | Map occupies upper region; two location rows; service row; 28 sp fare, method row, one fixed Request taxi | Edit locations; inspect breakdown; select actual method; Now/Later where available; request once | J/F/W/M; point edits invalidate quote; no fare/button enabled until authoritative prerequisites hold |
| R06 Fare detail | Readable line-item sheet, estimate/final qualifier at top, total at bottom | Close; refresh if quote expired; no arbitrary fare edit | W/R; server components only; tariff version remains audit metadata |
| R07 Payment method | Dedicated short choice sheet, cash default when authorized, other real capability rows | Select cash / configured manual bank or M-Wallet transfer; confirm choice | W/F; no card-entry form, wallet balance or unsupported payment icon; disabled capability explained |
| R08 Request pending | Review stays stable; footer busy; concise status above action; map not blocked by theatre | No second submit; reconcile uncertain outcome; Back does not cancel an unknown request | F/J; timeout never offers blind duplicate request |
| R09 Matching | Compact panel “Waiting for a driver”, journey summary, subtle contained loader, honest explanatory sentence | Permitted Cancel via review; Help; refresh/reconnect | J/R/M; no animated supply markers, invented percentage or guaranteed countdown |
| R10 Unmatched | Static neutral state “No taxi accepted this request”, trip retained in history | Try again through valid new-ride flow; Edit trip; view retained request | J/R; no false assignment or generic failure that loses history |
| R11 Assigned | Trip-phase title, authorized C12 driver/vehicle identity, pickup summary, readable fare/payment | Supported coordination; Safety; permitted cancellation review | J/M/R; identity shown only after server acceptance; photo/rating absent unless authorized data exists |
| R12 Driver approaching | Same stable identity and phase panel; route/last-known driver position secondary | Pickup detail; supported coordination; Safety; permitted cancel | J/M; location timestamp visible; stale marker remains honest; no fabricated continuous tracking |
| R13 Driver arrived | “Your taxi has arrived” only on confirmed state; taxi identifier most prominent | Verify vehicle information; allowed coordination; Safety | J/R; no passenger “start ride” command that manufactures driver state |
| R14 In ride | Minimal map and destination/status panel, driver/taxi identity collapsed but reachable, safety fixed | View trip; supported coordination/safety; no ordinary cancellation if API disallows it | J/M; no passenger maneuver list or editable price; interruption keeps last confirmed facts |
| R15 Cancellation review | Focused C22 with trip, consequence and current permitted policy | Confirm cancellation / Keep request; reason only if contract requires | F/J; API rejection/conflict refreshes status; dismissal never equals cancellation |
| R16 Cancelled / unavailable journey | Compact outcome panel with reason when safe and journey summary | New ride; Trips; Help | J/R; no rerunning prior request automatically; cancelled receipt does not imply payment |
| R17 Completed / cash pending | “Trip complete” separated from “Cash not confirmed”, final fare dominant, secondary trip context | View receipt; Rate if allowed; Help; return Ride | W/J/R; completion is not payment success; missing final fare explicitly unavailable |
| R18 Receipt | Full-page transaction document with date, locations, final amount, method/status, line items and refunds | Copy authorized reference; Help about this trip; rating link; Back | W/R; pending/processing/completed/refunded distinguishable without color; no internal IDs in main heading |
| R19 Manual-transfer instructions | Receipt-owned exact recipient and reference in read-only rows, concise external-payment explanation | Copy recipient/reference; submit payment claim where permitted; refresh | W/F; no financial credentials/upload; claim is not verified success; hidden if capability unavailable |
| R20 Transfer processing / refund detail | Static ledger rows with state/date/amount, original fare retained | Refresh; Help; inspect confirmed refund rows | W/R; partial refund shows recorded refunded total/net; full refund never asks passenger to pay again |
| R21 Rating | Clear 1–5 labelled selectable rating, optional supported feedback, small trip context, fixed Submit | Submit once; Skip/Back; show stored server result on return | F/J; no tip flow; no coerced rating prompt; tactile/assistive star values |
| R22 Trip list | Dedicated page, Past/Upcoming segment where available, C25 rows, compact filter only if supported | Open trip; refresh; return current ride with prominent retained banner | R/J; empty differs from read failure; no UUID list titles or hidden active trip |
| R23 Trip detail | Human phase/date/location summary, fare/payment when authorized, receipt and help | Receipt; Help; stored rating view; Back preserves list position | R/W/J; no driver details beyond authorized contract; technical reference in secondary copy area |
| R24 Fixed-route directory | Dedicated catalogue with city scope, localized route names, start/end and flat fare; no live map supply | Choose route/direction; Back to Ride; refresh | R; routes remain visible without online drivers; unpublished/replaced versions absent |
| R25 Fixed-route direction | Static route map, explicit start/end/ordered stops, direction and fare, concise terms | Select outbound/inbound actual version; review request; inspect stops | M/R/W/F; no reverse-direction inference; static line is not driver movement |
| R26 Schedule selection | Date/time picker within real booking horizon, timezone/city label, surcharge and policy preview | Choose valid slot; Review scheduled request; Back | F/W; local civil time converted through existing trusted contract; no raw ISO timestamp field |
| R27 Schedule review | Journey rows, date/time, surcharge/fare breakdown and cancellation terms above fixed request | Confirm scheduled request; edit time/points; inspect terms | F/W/J; request does not guarantee assigned driver; incompatible quote/policy requires refresh |
| R28 Upcoming booking list | Chronological booking cards with received/committed/dispatch/unfulfilled labels | Open booking; refresh; return live trip where applicable | R/J; upcoming commitment is not active ride; no countdown implying guarantee |
| R29 Booking detail / cancellation | Booking summary, commitment state/timeline, terms and fee/refund facts | Permitted cancellation via review; supported coordination; refresh | F/J/W; driver/time changes reconcile; handoff shows real live ride only when server returns it |
| R30 Account | Dedicated list page, full display name allowed to wrap, Profile/Inbox/Help/Language/Style/Sign out | Open one destination; edit only supported account fields | R; no decorative finance/dashboard tiles or fake verification tick |
| R31 Profile edit | Single-task display-name form, existing read-only contact information only if authorized | Save display name; Cancel; success after refresh | F; role/contact/security credentials cannot be changed through this form |
| R32 Inbox | Notification rows with safe title/date/read state; refresh in page bar | Open authorized target; Mark read where supported | R/F; payload only hints refresh; missing/restricted target explicit; no notification-authoritative trip state |
| R33 Help hub | Short categories, trip context entry, ordinary-support/safety distinction | Choose category/trip; view own cases; safety entry while assigned | R; no promise of 24/7 emergency service absent operation acceptance |
| R34 Support case creation | Labelled category/context/message fields and concise privacy guidance | Submit; Cancel; retain safe draft on failure | F; own authorized resources only; confirmed case ID rendered as human reference |
| R35 Own support case / timeline | State, last update, participant-safe messages and allowed next action | Refresh; supported response/close only when contract exists | R/F; no private staff notes, actor IDs or invented chat delivery/read receipts |
| R36 Safety during trip | Focused shield title, immediate truthful instructions, trip context, supported safety action | Submit supported report; supported emergency link only after approved local service contract | J/F; no fake “help is on the way”; actual response readiness remains pilot gate |
| R37 Assigned coordination | Bounded predefined/message input only as supported, confirmed latest signal and time | Send supported signal; refresh; return trip | F/J; no general-purpose messaging/call integration; unknown result retains draft without success |
| R38 Recent destination chooser | Own backend-owned trip destinations as a labelled list, with map alternative | Select recent destination; choose on map | R/M; recent history is not persistent Home/Work; no saved-place write |
| R39 Own safety reports | Report category/state and latest participant-safe response, linked trip | View existing safe report summary; create report for permitted ride | R; no staff notes or implied emergency response |
| R40 Safety report creation | Permitted trip selector, controlled safety category, bounded description and non-emergency warning | Submit; Cancel; safe draft retained on failure | F/J; no free chat or emergency dispatch; only own reportable ride |
| R41 Service-city selector | Public service-city list with actual localized names and scope context | Select city for route catalogue; refresh | R; city visibility is not driver availability or operating authorization |
| R42 Development coordinate fallback | Explicit development-only heading; latitude/longitude for pickup/destination with units | Validate map-point draft; return to map | F/M; hidden in consumer builds; coordinate shape checks never authorize pickup area |

## Driver onboarding, work and financial recovery

Source: `feature/driver/DriverHome.kt`, `feature/driver/onboarding/DriverOnboardingScreen.kt`,
`CityAuthorizationPresentation.kt`, driver profile/offer/ride/earning gateways,
shared coordinator and foreground-location policy. Onboarding must remain
consistent with the [applicant web pages](web-pages.md).

| ID / page | Layout and visual hierarchy | Fields/options and next actions | Profiles / specific acceptance |
| --- | --- | --- | --- |
| D00 Onboarding overview | Eligibility/status headline, short checklist, city/operator context; no dispatch map | Continue application; inspect required steps; Sign out | R; account creation, membership and dispatch authorization are distinct |
| D01 City / application selection | Labelled city and service choices from actual catalogue, requirement explanation | Choose permitted application context; start/open own application | R/F; no arbitrary city UUID field or inference of permission |
| D02 Identity / credentials | Requirement-led form grouped by real category, status per item | Enter supported data; continue; draft save where API supports | F; private fields minimized; server validation repeated; no fake “verified” badge |
| D03 Document requirements | C29 slots per required item, explicit file limits/types and capability state | Upload/replace/delete only where supported; inspect own metadata | F/R; hidden/disabled honestly if storage/scanning unavailable; no raw-file local persistence |
| D04 Vehicle application | Make/model/color/taxi ID fields and backend-required capacity/type; section review | Create/select actual vehicle; update permitted draft; continue | F; submission not verification; no decorative generic luxury vehicle selector |
| D05 Application review / submit | Readable summary with incomplete requirements and explicit final submit | Edit section; Submit; Back | F; version conflict and double-submit controlled; no online transition |
| D06 Application status | Static server timeline, current pending/more-info/approved/rejected/withdrawn state, safe explanation | Supply requested info; permitted withdrawal; refresh | R/F; no fabricated review ETA; rejected reason role-safe; approval not blanket city dispatch |
| D07 Eligibility restriction | Clear blocker title, action checklist for vehicle/credential/city/GPS/session; next useful action | Open affected requirement/settings; refresh; Help | R; do not show Go online as apparently functional behind restriction |
| D10 Offline work home | Map with compact city/status; primary 64 dp Go online; selected vehicle row; older pending-cash warning secondary | Go online; vehicle selection; Upcoming where enabled; Earnings | R/M/F; location/credential/network prerequisites evaluated by server; no status switch optimism |
| D11 Location / network diagnostic | Focused checklist with measured freshness/accuracy and permission guidance | Request new foreground observation; open native settings if appropriate; retry | M/R/F; observation acquisition time preserved; no fabricated GPS quality bars |
| D12 Online waiting | Quiet map, confirmed Online status, compact next-work panel, fixed Go offline | Go offline; authorized upcoming work; inspect material health issue | R/M/J; no live-supply heatmap/gamification or fictitious demand forecast |
| D13 Incoming immediate offer | Full readable job panel: pickup, destination, timing, fare/fee/net; fixed Accept and distinct Decline | Accept / Decline; inspect allowed details without hiding footer | F/J/W; fixed targets; server/monotonic timer; invalid/expired time disables Accept and refreshes |
| D14 Fixed-route / scheduled offer | Same skeleton with direction/flat fare or future date/terms/expected net visible | Accept / Decline; inspect terms | F/J/W; future commitment not active trip; no automatic acceptance or acceptance-rate pressure |
| D15 Offer expired / lost / uncertain | Neutral status on same stable card footprint; preserve reason and next step | Refresh current work; return available state only after server reload | R/F/J; lost race cannot appear assigned; no replay expired offer |
| D16 Assigned / navigate to pickup | Current job title, pickup dominant, route guidance/map, passenger-safe context, next permitted transition | Begin en-route if required; supported navigation handoff; coordination; cancel review where allowed | J/M/F; no turn-by-turn claim unless actual integration; not a passenger-side maneuver list |
| D17 At pickup | Confirmed arrival state, pickup details, coordination and Start ride as allowed | Arrive command if not yet confirmed; Start ride through backend; Help | J/F; location/phase prereqs fail closed; no swipe-only essential command |
| D18 In trip | Map/guidance dominant, destination and status compact, stable Complete trip action | Complete through review where necessary; supported Safety/Help | J/M/F; secondary account/finance work not competing with active control |
| D19 Completion review | Destination/trip/finalization explanation in focused C22, explicit action | Confirm complete / Keep trip active | F/J/W; server finalization may differ from quote; offline not local completion |
| D20 Cash confirmation | Final server amount, clear “Cash not confirmed”, trip/date, fixed confirmation | Confirm cash received after review; Back to pending queue | F/W; no preset settled tick; no earning from local completion; duplicate safe reconciliation |
| D21 Pending cash queue | Dedicated oldest-first C20 cards; badge visible on idle Work/Earnings; pagination | Open item; Reload; previous/next only if supported | R/W; failed queue read is not empty; selected page preserved on ordinary refresh |
| D22 Cash review / outcome | Exact trip/date/amount and irreversible financial meaning stated; confirmation separate from trip completion | Confirm received / Cancel; successful result reloads queue and earnings | F/W; unknown outcome reconciles first; settled item not repeated; survives restart |
| D23 Earnings | Compact real summary and clearly dated server earning rows, amount/fee/net hierarchy | Open record; refresh; pending-cash entry | R/W; no invented weekly totals, payout balance, chart or bank-transfer withdrawal |
| D24 Earning / trip detail | Gross/fee/net, recorded settlement state/date, trip context and permitted rating | Return to list; Help; inspect stored facts | R/W/J; human identifiers primary; no user-controlled finance state |
| D25 Work history | Dedicated C25 list; Past/Upcoming where enabled; current-work banner retained | Open trip; refresh; Back preserves position | R/J; no phase action replay from old trip detail |
| D26 Upcoming commitments | Chronological date/time, pickup/direction, commitment/status/terms | Open commitment; supported cancellation; refresh | R/J/W; future commitment does not show “On trip” |
| D27 Commitment detail / handoff | Job/time/terms, server timeline, upcoming-to-active handoff explicit | Allowed cancel/review; open current job only after returned authoritative handoff | F/J/W; no local countdown promotion into an active ride |
| D28 Driver account | Full name, eligibility summary, vehicle/application/inbox/help/language/style entries | Open supported detail; Sign out | R; no inferred identity from vehicle or offer |
| D29 Vehicles | Verified/pending/rejected labels, actual taxi identity, selected vehicle check | Register; select only verified/eligible vehicle through API; view detail | R/F; verified vehicle does not by itself guarantee driver eligibility |
| D30 Vehicle registration / detail | Single-task real model fields, status and active selection read-only where appropriate | Save registration; permitted selection; Back | F/R; no schema/API expansion for design convenience |
| D31 Driver inbox | Shared C26 page in driver context, safe work-resource links | Open/refresh authorized work; mark read | R/F/J; stale push never advances offer/trip/payment |
| D32 Driver Help / own case | Shared support structure, relevant work/payment context, participant-safe timeline | Create supported case; inspect own case; return current work | R/F/W; no earnings disputes resolved by a client flag |
| D33 Driver safety / coordination | Shared truthful safety/coordination structure, current job remains dominant | Send supported signal/report; return active work | J/F; no emergency-response claim or general chat/call invention |
| D34 Scheduled-offer preferences | One authorized city per row, unset/enabled/disabled server label | Receive future offers; stop future offers; refresh | R/F; distinct from going online and existing commitments; no optimistic toggle |
| D35 Cooperative membership | Actual cooperative name, membership state/number/joined date in read-only detail | Back; refresh authorized profile | R; supported read-only data, not a new governance feature; no voting/dashboard invented |
| D36 Professional credentials | Credential type/status/issue/expiry with human labels and next eligibility step | Inspect supported status; open application; refresh | R; no local verification or unrestricted professional-document preview |
| D37 Vehicle deactivation review | Exact vehicle/plate/current-selection context and dispatch consequence | Deactivate through existing command; Cancel | F/J; no local deactivation/eligibility mutation; active-trip conflict reconciles |
| D38 Online city/service choice | Actual authorized markets/services and selected verified vehicle | Choose legitimate city/service; submit availability | R/F/M; no account role picker; eligibility/location checked server-side |
| D39 Driver safety report history | Own report category/state/latest public message and trip context | Inspect permitted summary; create report | R/J; no staff-only narrative or emergency guarantee |
| D40 Driver safety report creation | Own authorized trip, controlled category, description, non-emergency warning | Submit; Cancel; return current job | F/J; no free-form coordination chat; server owns report creation |
| D41 Immediate fixed-route offer | Explicit published direction/start/end/flat fare, server timing, fixed Accept/Decline | Accept or decline actual offered version; review economics | F/J/W; separate composition from future scheduled commitment; static route not live supply |

## Documented future surfaces: design them, do not fake them

| ID / surface | Proposed composition and options | Capability/release boundary |
| --- | --- | --- |
| L00 Auth-method chooser / OTP phone entry | Short method list, country-aware phone field, one Continue | No alpha destination. Contact-verification provider/API/policy approval required; current password auth uses S03 |
| L01 OTP verification / resend | Six-digit or actual contracted length, paste/autofill, masked contact, truthful resend timer | Provider delivery/rate-limit/recovery contract required; no decorative OTP demo |
| L02 Saved Home/Work / saved-place editor | Labelled authorized place list; add/edit/delete name + confirmed map location | Persistence API/privacy approval; current recent destinations are not saved places |
| L03 Service-category chooser | Compact labelled actual capability rows, capacity/fare qualifiers | City config and matching support required; no luxury/XL/intercity option invented |
| L04 Card checkout / wallet / payout | Provider-owned secure handoff and truthful status, not a custom sensitive-data form | Financial/provider/legal work belongs to B/C; cash remains essential |
| L05 Continuous tracking / live trip sharing | Explicit consent, timestamp, authorized marker and sharing status | Location/tracking/provider/privacy contracts and native field acceptance required |
| L06 Contact verification / account export-delete | Single-task status/request page with clear consequences and follow-up | GAP/legal/API work required; no pretend buttons in Account |
| L07 General messaging / masked calls / emergency integration | Context-bound communication UI with delivery/availability facts | API/provider/operational acceptance required; current coordination remains bounded |
| L08 Cooperative governance/voting | Purpose-specific list/detail/review with role-safe records | Voting/governance require separate product/backend approval; existing read-only membership is D35 and scheduling preference is D34 |

## Detailed interaction specimens for the hardest pages

**R05 review:** page reads pickup → destination → estimated fare → payment method
→ Request taxi. Fare appears once as the primary amount; details open a separate
sheet. A point edit immediately marks the quote invalid. During submit, the footer
keeps height and says Requesting; a timeout says confirmation could not be obtained
and reconciles. The exact backend status determines matching/assigned/unmatched.

**R11 assigned:** phase above identity; taxi identifier and make/color below name;
pickup and meaningful ETA only when returned. A missing photo uses a neutral
silhouette. Safety and supported coordination are visible text actions. A stale
map cannot hide confirmed assignment or claim the driver moved.

**D13 offer:** pickup is the first large text, destination next, server timing in
fixed tabular digits, fare/fees/net grouped. Accept and Decline stay fixed above
the safe area. Fare details may expand, but never displace those controls. At
invalid/zero timing, Accept is unavailable and the refresh explanation is visible.

**D21 recovery:** queue is separate from earnings and history pagination. Each
card reads “Cash not confirmed”, amount, trip/date and Review. Opening a completed
ride does not perform cash settlement. After confirmation, both queue and earnings
reload. Offline/restart/session expiry preserves only safe navigation context;
payment facts are retrieved again.

## Mapping the old extended specification

| Existing IDs / headings | Proposed surfaces |
| --- | --- |
| P00–P01 | S00/S02 |
| P02–P05 (method/phone/OTP/email) | S03/S04 for current password identity; L00/L01 for deferred OTP |
| P06–P08 | R31, S10/S11 |
| P10–P13 | R00–R05 (R04 is later search) |
| P14/P14A | R24/R25 and L03 if new categories are later approved |
| P15–P18 | R06/R07/R05/R08/R09 |
| P19–P24 | R11–R14/R17/R21 |
| P25–P30 | R22/R23/L02/R30/R31/R33–R36 |
| D00–D04 | D00–D07 |
| D10–D17 | D10–D20 (review and uncertainty surfaces explicit) |
| D20–D22 | D21–D25/D28–D30 |
| Fixed routes / scheduled additions | R24–R29/D14/D26/D27 |
| Notifications, recovery, support/safety additions | S06–S09/R32–R37/D31–D33 |

Before implementing a family, reconcile its actual call sites and API capabilities
against the current checkout; this planning inventory is not a frozen code audit.
All unmapped UI discovered during the implementation inventory is logged and
specified before it is restyled. No old legacy page is left in the rejected chrome
on a demonstrated journey. Secondary/future scope follows [delivery.md](delivery.md).
