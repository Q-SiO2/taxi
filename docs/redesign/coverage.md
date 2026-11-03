# Source coverage audit

Prepared from the actual checkout on 2026-10-22. This inventories shared mobile, Android/iOS map presentation and applicant/operations Compose declarations. A composable is not automatically a page; reusable components, shells and presentation helpers are classified separately. Proposed splits and future capability views remain design surfaces, not implemented routes.

[Open every page](page-atlas.html). [Machine inventory](source-ui-inventory.json). [Source-file hashes](source-ui-files.json).

## Reconciliation

New source-backed views added after the owner challenged representative-screen coverage: active sessions, password changes, recovery custody, recent destinations, safety history/create, city selection, driver scheduling preferences, membership, credentials, vehicle deactivation, immediate fixed-route offers, authorization actions, assignment/boundary editors, recipient/capability creation and lifecycle reviews, MFA saved-code mode, restricted safety detail, retention/holds, overdue alert detail, policy/route lifecycle reviews, separate support triage, selected city detail and readiness review.

Corrected unsupported account search, recipient pause/activate, arbitrary support assignee/category, invented operator identity field and requirement-wide service selector. Fee/scheduling, recruitment and refund editors now carry source-controlled fields and choices.

## Inventory method and limits

Scan named `@Composable` functions, preserving extension receiver and function name; include platform map functions. Inline composable lambdas and runtime navigation outcomes need their parent screen audit, not artificial page counts. Per-file source anchors are inspection pointers; they do not prove native visual acceptance. Page-specific control/behavior review and actual Compose renders remain mandatory after approval.

## Declarations

| Source declaration | Kind | Planned surfaces/components |
| --- | --- | --- |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/App.kt:31` · `App` | composition shell | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/account/AccountSecuritySection.kt:39` · `AccountSecuritySection` | page/detail/editor | [S14](page-atlas.html#S14); [S15](page-atlas.html#S15); [S16](page-atlas.html#S16); [S17](page-atlas.html#S17); [S18](page-atlas.html#S18); [S19](page-atlas.html#S19) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:32` · `NotificationInboxSection` | page/detail/editor | [R32](page-atlas.html#R32); [D31](page-atlas.html#D31) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:58` · `AppNotification.localizedCopy` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:102` · `SupportTicketSection` | page/detail/editor | [R34](page-atlas.html#R34); [R35](page-atlas.html#R35); [D32](page-atlas.html#D32) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:158` · `SafetyReportSection` | page/detail/editor | [R39](page-atlas.html#R39); [R40](page-atlas.html#R40); [D39](page-atlas.html#D39); [D40](page-atlas.html#D40) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:239` · `supportCategoryLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:249` · `supportStatusLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:260` · `safetyCategoryLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/SharedSections.kt:274` · `safetyStatusLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:60` · `TaxiMobileScreen` | composition shell | [S00](page-atlas.html#S00); [S01](page-atlas.html#S01); [S02](page-atlas.html#S02); [S03](page-atlas.html#S03); [S04](page-atlas.html#S04); [S05](page-atlas.html#S05); [S06](page-atlas.html#S06); [S07](page-atlas.html#S07); [S08](page-atlas.html#S08); [S09](page-atlas.html#S09); [S10](page-atlas.html#S10); [S11](page-atlas.html#S11); [S12](page-atlas.html#S12); [S13](page-atlas.html#S13) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:256` · `GatePage` | composition shell | [S00](page-atlas.html#S00); [S01](page-atlas.html#S01); [S02](page-atlas.html#S02); [S03](page-atlas.html#S03); [S04](page-atlas.html#S04); [S05](page-atlas.html#S05); [S06](page-atlas.html#S06); [S07](page-atlas.html#S07); [S08](page-atlas.html#S08); [S09](page-atlas.html#S09); [S10](page-atlas.html#S10); [S11](page-atlas.html#S11); [S12](page-atlas.html#S12); [S13](page-atlas.html#S13) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:283` · `SessionLoadingScreen` | page/detail/editor | [S00](page-atlas.html#S00) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:302` · `SignedOutContent` | page/detail/editor | [S03](page-atlas.html#S03); [S04](page-atlas.html#S04); [S05](page-atlas.html#S05); [S06](page-atlas.html#S06); [S07](page-atlas.html#S07) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:513` · `WelcomeContent` | page/detail/editor | [S02](page-atlas.html#S02) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:557` · `DriverApplicationRequiredContent` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:574` · `DriverApplicationPendingContent` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:595` · `OfflineScreen` | page/detail/editor | [S09](page-atlas.html#S09) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/app/TaxiMobileScreen.kt:609` · `UpgradeRequiredScreen` | page/detail/editor | [S01](page-atlas.html#S01) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:127` · `DriverHome` | composition shell | [D07](page-atlas.html#D07); [D10](page-atlas.html#D10); [D11](page-atlas.html#D11); [D12](page-atlas.html#D12); [D13](page-atlas.html#D13); [D14](page-atlas.html#D14); [D15](page-atlas.html#D15); [D16](page-atlas.html#D16); [D17](page-atlas.html#D17); [D18](page-atlas.html#D18); [D19](page-atlas.html#D19); [D20](page-atlas.html#D20); [D23](page-atlas.html#D23); [D24](page-atlas.html#D24); [D25](page-atlas.html#D25); [D26](page-atlas.html#D26); [D27](page-atlas.html#D27); [D28](page-atlas.html#D28); [D29](page-atlas.html#D29); [D30](page-atlas.html#D30); [D31](page-atlas.html#D31); [D32](page-atlas.html#D32); [D33](page-atlas.html#D33); [D34](page-atlas.html#D34); [D35](page-atlas.html#D35); [D36](page-atlas.html#D36); [D37](page-atlas.html#D37); [D38](page-atlas.html#D38); [D41](page-atlas.html#D41) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:396` · `DriverToolbar` | page/detail/editor | [D11](page-atlas.html#D11) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:421` · `DriverOperationsSheet` | page/detail/editor | [D10](page-atlas.html#D10); [D12](page-atlas.html#D12); [D13](page-atlas.html#D13); [D15](page-atlas.html#D15); [D16](page-atlas.html#D16); [D17](page-atlas.html#D17); [D18](page-atlas.html#D18); [D19](page-atlas.html#D19); [D20](page-atlas.html#D20); [D38](page-atlas.html#D38); [D41](page-atlas.html#D41) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:739` · `DriverScheduledSheet` | page/detail/editor | [D14](page-atlas.html#D14); [D26](page-atlas.html#D26); [D27](page-atlas.html#D27); [D34](page-atlas.html#D34) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:882` · `TimedOfferCard` | page/detail/editor | [D13](page-atlas.html#D13); [D14](page-atlas.html#D14); [D41](page-atlas.html#D41) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:939` · `DriverCompletionControls` | page/detail/editor | [D19](page-atlas.html#D19); [D20](page-atlas.html#D20) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:982` · `DriverAccountSheet` | page/detail/editor | [D28](page-atlas.html#D28); [D35](page-atlas.html#D35); [D36](page-atlas.html#D36); [S14](page-atlas.html#S14); [S15](page-atlas.html#S15); [S16](page-atlas.html#S16); [S17](page-atlas.html#S17); [S18](page-atlas.html#S18); [S19](page-atlas.html#S19) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1124` · `DriverSafetySheet` | page/detail/editor | [D33](page-atlas.html#D33) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1143` · `DriverRideHistoryDetail` | page/detail/editor | [D24](page-atlas.html#D24) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1174` · `DriverEarningCard` | page/detail/editor | [D23](page-atlas.html#D23); [D24](page-atlas.html#D24) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1230` · `DriverVehicleSection` | page/detail/editor | [D29](page-atlas.html#D29); [D30](page-atlas.html#D30); [D37](page-atlas.html#D37) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1348` · `DriverInboxSheet` | page/detail/editor | [D31](page-atlas.html#D31) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/DriverHome.kt:1360` · `vehicleVerificationLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/CityAuthorizationPresentation.kt:21` · `CityAuthorizationSummary` | page/detail/editor | [D07](page-atlas.html#D07) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:63` · `DriverOnboardingScreen` | composition shell | [D00](page-atlas.html#D00); [D01](page-atlas.html#D01); [D02](page-atlas.html#D02); [D03](page-atlas.html#D03); [D04](page-atlas.html#D04); [D05](page-atlas.html#D05); [D06](page-atlas.html#D06) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:226` · `RecruitingCities` | page/detail/editor | [D01](page-atlas.html#D01) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:282` · `ApplicationDetail` | page/detail/editor | [D00](page-atlas.html#D00); [D05](page-atlas.html#D05); [D06](page-atlas.html#D06) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:577` · `RequirementEditor` | page/detail/editor | [D02](page-atlas.html#D02); [D03](page-atlas.html#D03) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:706` · `EvidenceChoices` | page/detail/editor | [D03](page-atlas.html#D03) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:733` · `ApplicantVehicleForm` | page/detail/editor | [D04](page-atlas.html#D04) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/onboarding/DriverOnboardingScreen.kt:801` · `ApplicationTimeline` | page/detail/editor | [D06](page-atlas.html#D06) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/driver/PendingCashPaymentsSection.kt:22` · `PendingCashPaymentsSection` | page/detail/editor | [D21](page-atlas.html#D21); [D22](page-atlas.html#D22) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.kt:11` · `rememberMapCoordinateSelection` | shared component | [C10](components.md); [C16](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.kt:20` · `MapLibreTripMap` | shared component | [C10](components.md); [C16](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:186` · `PassengerHome` | composition shell | [R00](page-atlas.html#R00); [R01](page-atlas.html#R01); [R02](page-atlas.html#R02); [R03](page-atlas.html#R03); [R05](page-atlas.html#R05); [R06](page-atlas.html#R06); [R07](page-atlas.html#R07); [R08](page-atlas.html#R08); [R09](page-atlas.html#R09); [R10](page-atlas.html#R10); [R11](page-atlas.html#R11); [R12](page-atlas.html#R12); [R13](page-atlas.html#R13); [R14](page-atlas.html#R14); [R15](page-atlas.html#R15); [R16](page-atlas.html#R16); [R17](page-atlas.html#R17); [R18](page-atlas.html#R18); [R19](page-atlas.html#R19); [R20](page-atlas.html#R20); [R21](page-atlas.html#R21); [R22](page-atlas.html#R22); [R23](page-atlas.html#R23); [R24](page-atlas.html#R24); [R25](page-atlas.html#R25); [R26](page-atlas.html#R26); [R27](page-atlas.html#R27); [R28](page-atlas.html#R28); [R29](page-atlas.html#R29); [R30](page-atlas.html#R30); [R31](page-atlas.html#R31); [R32](page-atlas.html#R32); [R33](page-atlas.html#R33); [R38](page-atlas.html#R38); [R41](page-atlas.html#R41); [R42](page-atlas.html#R42) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:546` · `PassengerToolbar` | composition shell | [R00](page-atlas.html#R00); [R01](page-atlas.html#R01); [R02](page-atlas.html#R02); [R03](page-atlas.html#R03); [R05](page-atlas.html#R05); [R06](page-atlas.html#R06); [R07](page-atlas.html#R07); [R08](page-atlas.html#R08); [R09](page-atlas.html#R09); [R10](page-atlas.html#R10); [R11](page-atlas.html#R11); [R12](page-atlas.html#R12); [R13](page-atlas.html#R13); [R14](page-atlas.html#R14); [R15](page-atlas.html#R15); [R16](page-atlas.html#R16); [R17](page-atlas.html#R17); [R18](page-atlas.html#R18); [R19](page-atlas.html#R19); [R20](page-atlas.html#R20); [R21](page-atlas.html#R21); [R22](page-atlas.html#R22); [R23](page-atlas.html#R23); [R24](page-atlas.html#R24); [R25](page-atlas.html#R25); [R26](page-atlas.html#R26); [R27](page-atlas.html#R27); [R28](page-atlas.html#R28); [R29](page-atlas.html#R29); [R30](page-atlas.html#R30); [R31](page-atlas.html#R31); [R32](page-atlas.html#R32); [R33](page-atlas.html#R33); [R38](page-atlas.html#R38); [R41](page-atlas.html#R41); [R42](page-atlas.html#R42) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:570` · `PassengerRideSheet` | page/detail/editor | [R00](page-atlas.html#R00); [R01](page-atlas.html#R01); [R02](page-atlas.html#R02); [R03](page-atlas.html#R03); [R05](page-atlas.html#R05); [R06](page-atlas.html#R06); [R07](page-atlas.html#R07); [R08](page-atlas.html#R08); [R09](page-atlas.html#R09); [R10](page-atlas.html#R10); [R11](page-atlas.html#R11); [R12](page-atlas.html#R12); [R13](page-atlas.html#R13); [R14](page-atlas.html#R14); [R15](page-atlas.html#R15); [R16](page-atlas.html#R16); [R17](page-atlas.html#R17) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:847` · `PassengerScheduledSheet` | page/detail/editor | [R26](page-atlas.html#R26); [R27](page-atlas.html#R27); [R28](page-atlas.html#R28); [R29](page-atlas.html#R29) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1050` · `ScheduledCancellationTerms.localizedSummary` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1067` · `PassengerFixedRoutesSheet` | page/detail/editor | [R24](page-atlas.html#R24) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1163` · `FixedRouteDirectionCard` | page/detail/editor | [R25](page-atlas.html#R25) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1208` · `SelectionSummary` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1246` · `CoordinateFields` | page/detail/editor | [R42](page-atlas.html#R42) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1254` · `RecentDestinationSection` | page/detail/editor | [R38](page-atlas.html#R38) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1275` · `PassengerAccountSheet` | page/detail/editor | [R30](page-atlas.html#R30); [S14](page-atlas.html#S14); [S15](page-atlas.html#S15); [S16](page-atlas.html#S16); [S17](page-atlas.html#S17); [S18](page-atlas.html#S18); [S19](page-atlas.html#S19) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1339` · `PassengerSafetySheet` | page/detail/editor | [R36](page-atlas.html#R36) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1358` · `PassengerProfileSection` | page/detail/editor | [R31](page-atlas.html#R31) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1377` · `PassengerHistorySection` | page/detail/editor | [R22](page-atlas.html#R22) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1406` · `PassengerRideHistoryDetail` | page/detail/editor | [R23](page-atlas.html#R23) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1428` · `PassengerReceipt` | page/detail/editor | [R18](page-atlas.html#R18) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1471` · `RefundReceiptSummary` | page/detail/editor | [R20](page-atlas.html#R20) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1505` · `ManualTransferReceipt` | page/detail/editor | [R19](page-atlas.html#R19) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1597` · `RideRatingSection` | page/detail/editor | [R21](page-atlas.html#R21) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1626` · `PassengerInboxSheet` | page/detail/editor | [R32](page-atlas.html#R32) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1638` · `fareComponentLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1652` · `paymentMethodLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1663` · `paymentStatusLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PassengerHome.kt:1677` · `refundReasonLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PlaceDiscoverySection.kt:39` · `PlaceDiscoverySection` | page/detail/editor | [R04](page-atlas.html#R04) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/passenger/PlaceDiscoverySection.kt:195` · `placeKindLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/rides/RideCoordinationSection.kt:34` · `RideLatestCoordinationMessage` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/rides/RideCoordinationSection.kt:51` · `RideCoordinationActions` | page/detail/editor | [R37](page-atlas.html#R37); [D33](page-atlas.html#D33) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/ConfirmDialog.kt:16` · `ConfirmDialog` | shared component | [C22](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/DriverCard.kt:17` · `DriverCard` | shared component | [C12](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/FareBlock.kt:19` · `FareBlock` | shared component | [C11](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapFab.kt:21` · `MapFab` | shared component | [C02](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapToolbar.kt:36` · `MapToolbar` | shared component | [C06](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapToolbar.kt:84` · `MapToolbarAction` | shared component | [C06](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/MapToolbar.kt:112` · `MapToolbarGlyph` | shared component | [C06](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/OfferCard.kt:20` · `OfferCard` | shared component | [C13](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/OptionalArtwork.kt:52` · `rememberOptionalArtworkPainter` | shared component | [C39](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/Skeleton.kt:21` · `Skeleton` | shared component | [C19](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SpecializedFields.kt:34` · `EmailField` | shared component | [C03](components.md); [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SpecializedFields.kt:54` · `PasswordField` | shared component | [C03](components.md); [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SpecializedFields.kt:75` · `PhoneNumberField` | shared component | [C03](components.md); [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SpecializedFields.kt:120` · `OtpInput` | shared component | [C03](components.md); [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SpecializedFields.kt:165` · `RatingStars` | shared component | [C03](components.md); [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/StatusPill.kt:43` · `StatusPill` | shared component | [C17](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/SuccessConfirmation.kt:32` · `SuccessConfirmation` | shared component | [C18](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiArtwork.kt:40` · `TaxiBrandArtwork` | shared component | [C39](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiArtwork.kt:68` · `TaxiBrandFallbackArtwork` | shared component | [C39](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiArtwork.kt:126` · `EmptyState` | shared component | [C39](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiButton.kt:27` · `TaxiButton` | shared component | [C01](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiCards.kt:35` · `TaxiCard` | shared component | [C25](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiCards.kt:58` · `LocationSelectionField` | shared component | [C25](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiCards.kt:100` · `DriverDocumentCard` | shared component | [C25](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiCards.kt:117` · `PaymentMethodCard` | shared component | [C25](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiCards.kt:161` · `VehicleAssetFallback` | shared component | [C25](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiEntryFrame.kt:40` · `TaxiEntryFrame` | shared component | [C39](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiLanguageChooser.kt:32` · `TaxiLanguageChooser` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiSegmentedControl.kt:20` · `TaxiSegmentedControl` | shared component | [C05](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiSegmentedControl.kt:39` · `Segment` | shared component | [C05](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiSheet.kt:73` · `TaxiSheet` | shared component | [C08](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiStyleChooser.kt:39` · `TaxiStyleChooser` | shared component | [C04](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiTaskSurface.kt:23` · `taxiTaskSurface` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/TaxiTextField.kt:28` · `TaxiTextField` | shared component | [C03](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/components/ToastBanner.kt:22` · `ToastBanner` | shared component | [C18](components.md) |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/text/UiMessage.kt:17` · `UiMessage.resolve` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiStyle.kt:51` · `rememberTaxiStylePreferences` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiTheme.kt:22` · `TaxiTheme` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiTypography.kt:24` · `taxiArabicFontFamily` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiTypography.kt:31` · `taxiTypography` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/androidMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.android.kt:31` · `MapLibreTripMap` | shared component | [C10](components.md); [C16](components.md) |
| `TaxiMobile/shared/src/androidMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiStylePreferences.android.kt:8` · `rememberTaxiStylePreferences` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/shared/src/iosMain/kotlin/org/example/taximobile/feature/maps/MapLibreTripMap.ios.kt:31` · `MapLibreTripMap` | shared component | [C10](components.md); [C16](components.md) |
| `TaxiMobile/shared/src/iosMain/kotlin/org/example/taximobile/feature/ui/theme/TaxiStylePreferences.ios.kt:7` · `rememberTaxiStylePreferences` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantApplicationEditor.kt:55` · `ApplicantApplicationEditor` | page/detail/editor | [A04](page-atlas.html#A04); [A05](page-atlas.html#A05); [A06](page-atlas.html#A06); [A07](page-atlas.html#A07); [A08](page-atlas.html#A08); [A09](page-atlas.html#A09); [A10](page-atlas.html#A10); [A11](page-atlas.html#A11) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantApplicationEditor.kt:287` · `ApplicantRequirementEditor` | page/detail/editor | [A05](page-atlas.html#A05); [A06](page-atlas.html#A06) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantApplicationEditor.kt:409` · `EvidenceChoices` | page/detail/editor | [A06](page-atlas.html#A06) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantApplicationEditor.kt:436` · `ApplicantVehicleForm` | page/detail/editor | [A07](page-atlas.html#A07) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantApplicationEditor.kt:482` · `ApplicationTimeline` | page/detail/editor | [A09](page-atlas.html#A09) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantComponents.kt:32` · `ApplicantWordmark` | shared component | [C01](components.md); [C17](components.md); [C18](components.md); [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantComponents.kt:53` · `ApplicantCard` | shared component | [C01](components.md); [C17](components.md); [C18](components.md); [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantComponents.kt:74` · `ApplicantMessageBanner` | shared component | [C01](components.md); [C17](components.md); [C18](components.md); [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantComponents.kt:104` · `ApplicantPrimaryButton` | shared component | [C01](components.md); [C17](components.md); [C18](components.md); [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantComponents.kt:124` · `ApplicantStatus` | shared component | [C01](components.md); [C17](components.md); [C18](components.md); [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantPortalApp.kt:57` · `ApplicantPortalApp` | composition shell | [A00](page-atlas.html#A00); [A01](page-atlas.html#A01); [A02](page-atlas.html#A02); [A03](page-atlas.html#A03); [A12](page-atlas.html#A12) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantPortalApp.kt:78` · `ApplicantWelcome` | page/detail/editor | [A00](page-atlas.html#A00) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantPortalApp.kt:122` · `WelcomePanel` | page/detail/editor | [A00](page-atlas.html#A00) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantPortalApp.kt:167` · `AuthenticationPanel` | page/detail/editor | [A01](page-atlas.html#A01); [A02](page-atlas.html#A02) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/applicant/ui/ApplicantPortalApp.kt:288` · `ApplicantDashboard` | page/detail/editor | [A03](page-atlas.html#A03); [A12](page-atlas.html#A12) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/AccountSecurityScreen.kt:37` · `AccountSecurityScreen` | page/detail/editor | [O53](page-atlas.html#O53); [O54](page-atlas.html#O54) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/AnalyticsScreen.kt:32` · `AnalyticsScreen` | page/detail/editor | [O45](page-atlas.html#O45); [O46](page-atlas.html#O46) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:110` · `CaseOperationsScreen` | composition shell | [O47](page-atlas.html#O47); [O48](page-atlas.html#O48); [O49](page-atlas.html#O49); [O50](page-atlas.html#O50); [O51](page-atlas.html#O51); [O52](page-atlas.html#O52); [O71](page-atlas.html#O71); [O72](page-atlas.html#O72); [O73](page-atlas.html#O73); [O74](page-atlas.html#O74); [O75](page-atlas.html#O75); [O84](page-atlas.html#O84); [O85](page-atlas.html#O85) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:237` · `OverdueAlertsSection` | page/detail/editor | [O75](page-atlas.html#O75) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:296` · `SupportQueueSection` | page/detail/editor | [O47](page-atlas.html#O47) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:338` · `SafetyQueueSection` | page/detail/editor | [O47](page-atlas.html#O47) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:380` · `QueueHeader` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:404` · `QueueText` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:410` · `RetentionSection` | page/detail/editor | [O52](page-atlas.html#O52); [O72](page-atlas.html#O72) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:477` · `SupportCaseFlow` | page/detail/editor | [O48](page-atlas.html#O48); [O49](page-atlas.html#O49); [O50](page-atlas.html#O50); [O84](page-atlas.html#O84) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:522` · `SupportCaseDetailDialog` | page/detail/editor | [O48](page-atlas.html#O48) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:585` · `SafetyCaseFlow` | page/detail/editor | [O71](page-atlas.html#O71); [O85](page-atlas.html#O85) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:650` · `CaseDetailBody` | page/detail/editor | [O48](page-atlas.html#O48); [O71](page-atlas.html#O71) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:713` · `SupportTriageDialog` | page/detail/editor | [O84](page-atlas.html#O84) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:734` · `SupportTransitionDialog` | page/detail/editor | [O49](page-atlas.html#O49) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:765` · `SafetyHandoffDialog` | page/detail/editor | [O50](page-atlas.html#O50) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:783` · `SafetyTransitionDialog` | page/detail/editor | [O85](page-atlas.html#O85) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:814` · `AlertAcknowledgementDialog` | page/detail/editor | [O51](page-atlas.html#O51) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:831` · `LegalHoldDialog` | page/detail/editor | [O73](page-atlas.html#O73); [O74](page-atlas.html#O74) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:863` · `CommandDialog` | shared component | [C22](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:890` · `ControlledChoice` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CaseOperationsScreen.kt:906` · `CommandText` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/CityAuthorizationReview.kt:33` · `CityAuthorizationReview` | page/detail/editor | [O62](page-atlas.html#O62); [O63](page-atlas.html#O63); [O64](page-atlas.html#O64); [O65](page-atlas.html#O65) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:48` · `CreateCityDialog` | page/detail/editor | [O07](page-atlas.html#O07) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:101` · `CreateOperatorDialog` | page/detail/editor | [O15](page-atlas.html#O15) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:146` · `CreateAssignmentDialog` | page/detail/editor | [O66](page-atlas.html#O66) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:185` · `CreateServiceAreaDialog` | page/detail/editor | [O67](page-atlas.html#O67) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:239` · `CreateConfigurationDialog` | page/detail/editor | [O10](page-atlas.html#O10) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:360` · `ControlPlaneReviewDialog` | page/detail/editor | [O09](page-atlas.html#O09); [O11](page-atlas.html#O11); [O16](page-atlas.html#O16) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:391` · `ControlPlaneConfirmDialog` | page/detail/editor | [O09](page-atlas.html#O09); [O11](page-atlas.html#O11); [O16](page-atlas.html#O16) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:472` · `EditorDialog` | shared component | [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:505` · `EditorField` | shared component | [C03](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:523` · `ChoiceChips` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ControlPlaneEditors.kt:538` · `RecordChoice` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:62` · `DriverRecruitmentScreen` | composition shell | [O31](page-atlas.html#O31); [O32](page-atlas.html#O32); [O33](page-atlas.html#O33); [O34](page-atlas.html#O34); [O35](page-atlas.html#O35); [O36](page-atlas.html#O36); [O78](page-atlas.html#O78) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:105` · `OnboardingAggregateSection` | page/detail/editor | [O31](page-atlas.html#O31) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:168` · `RequirementVersionSection` | page/detail/editor | [O32](page-atlas.html#O32) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:247` · `RequirementVersionEditor` | page/detail/editor | [O33](page-atlas.html#O33) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:331` · `RequirementItemEditor` | page/detail/editor | [O33](page-atlas.html#O33) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:405` · `LocalizedCopyFields` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:421` · `RequirementTransitionDialog` | page/detail/editor | [O78](page-atlas.html#O78) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:461` · `DriverReviewSection` | page/detail/editor | [O31](page-atlas.html#O31) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:493` · `DriverApplicationReview` | page/detail/editor | [O34](page-atlas.html#O34); [O36](page-atlas.html#O36); [O62](page-atlas.html#O62) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:589` · `DriverDecisionForm` | page/detail/editor | [O35](page-atlas.html#O35) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/DriverRecruitmentScreen.kt:695` · `ServiceCheckbox` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:54` · `FixedRoutesScreen` | composition shell | [O23](page-atlas.html#O23); [O24](page-atlas.html#O24); [O25](page-atlas.html#O25); [O26](page-atlas.html#O26); [O82](page-atlas.html#O82); [O83](page-atlas.html#O83) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:155` · `RouteScopeBanner` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:179` · `FixedRouteCard` | page/detail/editor | [O23](page-atlas.html#O23) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:248` · `GeometryPreview` | page/detail/editor | [O25](page-atlas.html#O25) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:281` · `RouteIdentityEditor` | page/detail/editor | [O24](page-atlas.html#O24) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:391` · `RouteVersionEditor` | page/detail/editor | [O25](page-atlas.html#O25) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:475` · `LocalizedFields` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:492` · `EditorField` | shared component | [C03](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/FixedRoutesScreen.kt:503` · `RouteCommandDialog` | page/detail/editor | [O26](page-atlas.html#O26); [O82](page-atlas.html#O82); [O83](page-atlas.html#O83) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:64` · `OperationsApp` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:103` · `OperationsLogin` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:175` · `LoginBrandPanel` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:206` · `LoginCard` | page/detail/editor | [O00](page-atlas.html#O00) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:296` · `OperationsMfaVerification` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:362` · `OperationsShell` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:403` · `OperationsSidebar` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:467` · `SidebarDestination` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:492` · `CompactNavigation` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:545` · `MfaStepUpDialog` | page/detail/editor | [O02](page-atlas.html#O02) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:579` · `OperationsWorkspace` | composition shell | [O00](page-atlas.html#O00); [O01](page-atlas.html#O01); [O02](page-atlas.html#O02); [O03](page-atlas.html#O03); [O04](page-atlas.html#O04); [O70](page-atlas.html#O70) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:661` · `ScopeTopBar` | page/detail/editor | [O03](page-atlas.html#O03) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:725` · `InitialLoading` | page/detail/editor | [O04](page-atlas.html#O04) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsApp.kt:739` · `LoadFailure` | page/detail/editor | [O04](page-atlas.html#O04) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:61` · `OperationsWordmark` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:95` · `StatusBadge` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:123` · `MessageBanner` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:164` · `MetricCard` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:190` · `SectionHeading` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:211` · `EmptyState` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:244` · `ScopeMenu` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:294` · `DataCard` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:326` · `KeyValue` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsComponents.kt:336` · `PageLimitNote` | shared component | [C17](components.md); [C18](components.md); [C30](components.md); [C31](components.md); [C32](components.md); [C39](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:95` · `recruitmentLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:107` · `recruitmentTextStyle` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:139` · `rolloutLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:164` · `paymentLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:221` · `caseLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsLabels.kt:249` · `bookingLabel` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:75` · `RolloutScreen` | page/detail/editor | [O05](page-atlas.html#O05) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:157` · `CitiesScreen` | page/detail/editor | [O06](page-atlas.html#O06) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:324` · `CityDetail` | page/detail/editor | [O86](page-atlas.html#O86) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:540` · `ReadinessGateGroup` | page/detail/editor | [O12](page-atlas.html#O12) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:588` · `ReadinessReviewDialog` | page/detail/editor | [O87](page-atlas.html#O87) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:639` · `OperatorsScreen` | page/detail/editor | [O14](page-atlas.html#O14) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:801` · `AuditScreen` | page/detail/editor | [O60](page-atlas.html#O60) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:836` · `LifecycleReviewDialog` | page/detail/editor | [O13](page-atlas.html#O13) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:882` · `ScreenColumn` | shared component | [C32](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:893` · `TableHeader` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:913` · `TableRow` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/OperationsScreens.kt:931` · `RowScope.TableCell` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:51` · `PaymentOperationsScreen` | composition shell | [O37](page-atlas.html#O37); [O38](page-atlas.html#O38); [O39](page-atlas.html#O39); [O40](page-atlas.html#O40); [O41](page-atlas.html#O41); [O42](page-atlas.html#O42); [O43](page-atlas.html#O43); [O68](page-atlas.html#O68); [O69](page-atlas.html#O69); [O76](page-atlas.html#O76); [O77](page-atlas.html#O77) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:88` · `RecipientCreator` | page/detail/editor | [O76](page-atlas.html#O76) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:118` · `RecipientList` | page/detail/editor | [O38](page-atlas.html#O38); [O68](page-atlas.html#O68) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:161` · `CapabilityCreator` | page/detail/editor | [O77](page-atlas.html#O77) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:219` · `CapabilityList` | page/detail/editor | [O39](page-atlas.html#O39); [O69](page-atlas.html#O69) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:236` · `CapabilityRow` | page/detail/editor | [O69](page-atlas.html#O69) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:267` · `TransferQueue` | page/detail/editor | [O40](page-atlas.html#O40); [O41](page-atlas.html#O41) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:303` · `RefundRecorder` | page/detail/editor | [O42](page-atlas.html#O42) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:332` · `RefundHistory` | page/detail/editor | [O43](page-atlas.html#O43) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:347` · `OperationsPanel` | shared component | [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:365` · `RecordSurface` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PaymentOperationsScreen.kt:378` · `Field` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:316` · `TariffEditor` | page/detail/editor | [O18](page-atlas.html#O18) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:372` · `FeePolicyEditor` | page/detail/editor | [O20](page-atlas.html#O20) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:417` · `SchedulingPolicyEditor` | page/detail/editor | [O22](page-atlas.html#O22) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:474` · `PolicyEditorFrame` | shared component | [C33](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:501` · `PolicyField` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:513` · `EffectiveFields` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:525` · `PolicyChoice` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsEditors.kt:551` · `ValidationAndSave` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:46` · `PricingEconomicsScreen` | composition shell | [O17](page-atlas.html#O17); [O19](page-atlas.html#O19); [O21](page-atlas.html#O21); [O79](page-atlas.html#O79); [O80](page-atlas.html#O80); [O81](page-atlas.html#O81) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:96` · `PricingScopeBanner` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:129` · `PricingMetrics` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:147` · `TariffSection` | page/detail/editor | [O17](page-atlas.html#O17) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:215` · `OperatorFeeSection` | page/detail/editor | [O19](page-atlas.html#O19) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:274` · `SchedulingPolicySection` | page/detail/editor | [O21](page-atlas.html#O21) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:332` · `PolicyCollection` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:342` · `PolicyCard` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/PricingEconomicsScreen.kt:381` · `PolicyTransitionDialog` | page/detail/editor | [O79](page-atlas.html#O79); [O80](page-atlas.html#O80); [O81](page-atlas.html#O81) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ScheduledExceptionsScreen.kt:31` · `ScheduledExceptionsScreen` | page/detail/editor | [O44](page-atlas.html#O44) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/ScheduledExceptionsScreen.kt:71` · `ScheduledExceptionCard` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:49` · `SecurityIncidentScreen` | composition shell | [O55](page-atlas.html#O55); [O56](page-atlas.html#O56); [O57](page-atlas.html#O57); [O58](page-atlas.html#O58); [O59](page-atlas.html#O59) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:97` · `CreateSecurityIncidentPanel` | page/detail/editor | [O55](page-atlas.html#O55) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:195` · `IncidentQueue` | page/detail/editor | [O55](page-atlas.html#O55) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:236` · `IncidentDetail` | page/detail/editor | [O56](page-atlas.html#O56) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:267` · `IncidentResponsibilitiesPanel` | page/detail/editor | [O56](page-atlas.html#O56) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:419` · `TimelinePanel` | page/detail/editor | [O57](page-atlas.html#O57) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:523` · `IncidentTransitionPanel` | page/detail/editor | [O58](page-atlas.html#O58) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:612` · `IncidentPostmortemPanel` | page/detail/editor | [O59](page-atlas.html#O59) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:728` · `TimestampFields` | presentation helper | Inherits parent layout/state; no separate navigation surface |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/SecurityIncidentScreen.kt:761` · `SecurityIncidentPanel` | shared component | [C23](components.md) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/StaffAccessScreen.kt:43` · `StaffAccessScreen` | composition shell | [O27](page-atlas.html#O27); [O28](page-atlas.html#O28); [O29](page-atlas.html#O29); [O30](page-atlas.html#O30) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/StaffAccessScreen.kt:287` · `CreateAdministrativeGrantDialog` | page/detail/editor | [O28](page-atlas.html#O28) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/StaffAccessScreen.kt:409` · `RevokeAdministrativeGrantDialog` | page/detail/editor | [O29](page-atlas.html#O29) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/operations/ui/StaffAccessScreen.kt:458` · `AdministrativeGrantDecisionDialog` | page/detail/editor | [O30](page-atlas.html#O30) |
| `TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/WebLanguageEnvironment.kt:32` · `WebLanguageEnvironment` | presentation helper | Inherits parent layout/state; no separate navigation surface |

## Page-by-page artifact ledger

| View | Blocks / content-control items | Composition | Specification |
| --- | --- | --- | --- |
| [S00 Session restore](page-atlas.html#S00) | 1 / 2 | status | [Full spec](pages/S00.md) |
| [S01 Compatibility gate](page-atlas.html#S01) | 1 / 3 | gate | [Full spec](pages/S01.md) |
| [S02 Welcome](page-atlas.html#S02) | 2 / 3 | welcome | [Full spec](pages/S02.md) |
| [S03 Sign in](page-atlas.html#S03) | 2 / 4 | auth | [Full spec](pages/S03.md) |
| [S04 Create account](page-atlas.html#S04) | 1 / 4 | form | [Full spec](pages/S04.md) |
| [S05 Account-created acknowledgement](page-atlas.html#S05) | 1 / 3 | status | [Full spec](pages/S05.md) |
| [S06 Recovery](page-atlas.html#S06) | 2 / 4 | form | [Full spec](pages/S06.md) |
| [S07 Recovery acknowledgement](page-atlas.html#S07) | 1 / 2 | status | [Full spec](pages/S07.md) |
| [S08 Session expired / revoked](page-atlas.html#S08) | 1 / 2 | gate | [Full spec](pages/S08.md) |
| [S09 Connection interruption](page-atlas.html#S09) | 2 / 5 | notice | [Full spec](pages/S09.md) |
| [S10 Location rationale](page-atlas.html#S10) | 1 / 3 | permission | [Full spec](pages/S10.md) |
| [S11 Notification rationale](page-atlas.html#S11) | 1 / 2 | permission | [Full spec](pages/S11.md) |
| [S12 Language / style](page-atlas.html#S12) | 3 / 4 | settings | [Full spec](pages/S12.md) |
| [S13 Sign-out confirmation](page-atlas.html#S13) | 1 / 3 | dialog | [Full spec](pages/S13.md) |
| [S14 Account security](page-atlas.html#S14) | 1 / 3 | settings | [Full spec](pages/S14.md) |
| [S15 Password change](page-atlas.html#S15) | 2 / 3 | form | [Full spec](pages/S15.md) |
| [S16 Active sessions](page-atlas.html#S16) | 2 / 3 | list | [Full spec](pages/S16.md) |
| [S17 Session revocation review](page-atlas.html#S17) | 1 / 4 | dialog | [Full spec](pages/S17.md) |
| [S18 Recovery-code generation](page-atlas.html#S18) | 2 / 2 | form | [Full spec](pages/S18.md) |
| [S19 One-time recovery-code custody](page-atlas.html#S19) | 2 / 4 | secrets | [Full spec](pages/S19.md) |
| [R00 Ride home](page-atlas.html#R00) | 2 / 5 | map-home | [Full spec](pages/R00.md) |
| [R01 Destination map](page-atlas.html#R01) | 2 / 3 | map-select | [Full spec](pages/R01.md) |
| [R02 Pickup map](page-atlas.html#R02) | 2 / 3 | map-select | [Full spec](pages/R02.md) |
| [R03 Point confirmation / fallback](page-atlas.html#R03) | 2 / 4 | map-review | [Full spec](pages/R03.md) |
| [R04 Optional place lookup](page-atlas.html#R04) | 2 / 3 | search | [Full spec](pages/R04.md) |
| [R05 Ride review](page-atlas.html#R05) | 3 / 5 | map-review | [Full spec](pages/R05.md) |
| [R06 Fare detail](page-atlas.html#R06) | 2 / 4 | receipt | [Full spec](pages/R06.md) |
| [R07 Payment method](page-atlas.html#R07) | 2 / 2 | choice | [Full spec](pages/R07.md) |
| [R08 Request pending](page-atlas.html#R08) | 2 / 4 | status | [Full spec](pages/R08.md) |
| [R09 Matching](page-atlas.html#R09) | 3 / 5 | map-status | [Full spec](pages/R09.md) |
| [R10 Unmatched](page-atlas.html#R10) | 2 / 4 | status | [Full spec](pages/R10.md) |
| [R11 Assigned](page-atlas.html#R11) | 3 / 6 | map-identity | [Full spec](pages/R11.md) |
| [R12 Driver approaching](page-atlas.html#R12) | 3 / 5 | map-trip | [Full spec](pages/R12.md) |
| [R13 Driver arrived](page-atlas.html#R13) | 2 / 4 | map-trip | [Full spec](pages/R13.md) |
| [R14 In ride](page-atlas.html#R14) | 3 / 5 | map-trip | [Full spec](pages/R14.md) |
| [R15 Cancellation review](page-atlas.html#R15) | 2 / 4 | dialog | [Full spec](pages/R15.md) |
| [R16 Cancelled / unavailable journey](page-atlas.html#R16) | 2 / 4 | status | [Full spec](pages/R16.md) |
| [R17 Completed / cash pending](page-atlas.html#R17) | 3 / 5 | completion | [Full spec](pages/R17.md) |
| [R18 Receipt](page-atlas.html#R18) | 3 / 7 | receipt | [Full spec](pages/R18.md) |
| [R19 Manual-transfer instructions](page-atlas.html#R19) | 2 / 4 | receipt | [Full spec](pages/R19.md) |
| [R20 Transfer processing / refund detail](page-atlas.html#R20) | 3 / 5 | receipt | [Full spec](pages/R20.md) |
| [R21 Rating](page-atlas.html#R21) | 3 / 3 | rating | [Full spec](pages/R21.md) |
| [R22 Trip list](page-atlas.html#R22) | 2 / 4 | list | [Full spec](pages/R22.md) |
| [R23 Trip detail](page-atlas.html#R23) | 3 / 7 | detail | [Full spec](pages/R23.md) |
| [R24 Fixed-route directory](page-atlas.html#R24) | 2 / 3 | catalog | [Full spec](pages/R24.md) |
| [R25 Fixed-route direction](page-atlas.html#R25) | 3 / 6 | map-route | [Full spec](pages/R25.md) |
| [R26 Schedule selection](page-atlas.html#R26) | 2 / 4 | date | [Full spec](pages/R26.md) |
| [R27 Schedule review](page-atlas.html#R27) | 4 / 8 | review | [Full spec](pages/R27.md) |
| [R28 Upcoming booking list](page-atlas.html#R28) | 1 / 3 | list | [Full spec](pages/R28.md) |
| [R29 Booking detail / cancellation](page-atlas.html#R29) | 3 / 7 | timeline | [Full spec](pages/R29.md) |
| [R30 Account](page-atlas.html#R30) | 2 / 7 | settings | [Full spec](pages/R30.md) |
| [R31 Profile edit](page-atlas.html#R31) | 2 / 2 | form | [Full spec](pages/R31.md) |
| [R32 Inbox](page-atlas.html#R32) | 2 / 3 | list | [Full spec](pages/R32.md) |
| [R33 Help hub](page-atlas.html#R33) | 2 / 5 | settings | [Full spec](pages/R33.md) |
| [R34 Support case creation](page-atlas.html#R34) | 1 / 4 | form | [Full spec](pages/R34.md) |
| [R35 Own support case / timeline](page-atlas.html#R35) | 3 / 5 | timeline | [Full spec](pages/R35.md) |
| [R36 Safety during trip](page-atlas.html#R36) | 3 / 4 | safety | [Full spec](pages/R36.md) |
| [R37 Assigned coordination](page-atlas.html#R37) | 2 / 2 | choice | [Full spec](pages/R37.md) |
| [R38 Recent destination chooser](page-atlas.html#R38) | 2 / 3 | list | [Full spec](pages/R38.md) |
| [R39 Own safety reports](page-atlas.html#R39) | 2 / 3 | list | [Full spec](pages/R39.md) |
| [R40 Safety report creation](page-atlas.html#R40) | 2 / 4 | form | [Full spec](pages/R40.md) |
| [R41 Service-city selector](page-atlas.html#R41) | 2 / 2 | choice | [Full spec](pages/R41.md) |
| [R42 Development coordinate fallback](page-atlas.html#R42) | 3 / 5 | developer | [Full spec](pages/R42.md) |
| [D00 Onboarding overview](page-atlas.html#D00) | 2 / 5 | checklist | [Full spec](pages/D00.md) |
| [D01 City / application selection](page-atlas.html#D01) | 2 / 3 | choice | [Full spec](pages/D01.md) |
| [D02 Identity / credentials](page-atlas.html#D02) | 2 / 4 | form | [Full spec](pages/D02.md) |
| [D03 Document requirements](page-atlas.html#D03) | 1 / 3 | documents | [Full spec](pages/D03.md) |
| [D04 Vehicle application](page-atlas.html#D04) | 2 / 8 | form | [Full spec](pages/D04.md) |
| [D05 Application review / submit](page-atlas.html#D05) | 2 / 6 | review | [Full spec](pages/D05.md) |
| [D06 Application status](page-atlas.html#D06) | 3 / 6 | timeline | [Full spec](pages/D06.md) |
| [D07 Eligibility restriction](page-atlas.html#D07) | 1 / 5 | gate | [Full spec](pages/D07.md) |
| [D10 Offline work home](page-atlas.html#D10) | 3 / 5 | map-work | [Full spec](pages/D10.md) |
| [D11 Location / network diagnostic](page-atlas.html#D11) | 2 / 5 | diagnostic | [Full spec](pages/D11.md) |
| [D12 Online waiting](page-atlas.html#D12) | 2 / 3 | map-work | [Full spec](pages/D12.md) |
| [D13 Incoming immediate offer](page-atlas.html#D13) | 3 / 7 | offer | [Full spec](pages/D13.md) |
| [D14 Fixed-route / scheduled offer](page-atlas.html#D14) | 4 / 9 | offer | [Full spec](pages/D14.md) |
| [D15 Offer expired / lost / uncertain](page-atlas.html#D15) | 1 / 3 | status | [Full spec](pages/D15.md) |
| [D16 Assigned / navigate to pickup](page-atlas.html#D16) | 3 / 4 | map-trip | [Full spec](pages/D16.md) |
| [D17 At pickup](page-atlas.html#D17) | 2 / 3 | map-trip | [Full spec](pages/D17.md) |
| [D18 In trip](page-atlas.html#D18) | 2 / 3 | map-trip | [Full spec](pages/D18.md) |
| [D19 Completion review](page-atlas.html#D19) | 2 / 4 | dialog | [Full spec](pages/D19.md) |
| [D20 Cash confirmation](page-atlas.html#D20) | 2 / 4 | cash | [Full spec](pages/D20.md) |
| [D21 Pending cash queue](page-atlas.html#D21) | 2 / 4 | queue | [Full spec](pages/D21.md) |
| [D22 Cash review / outcome](page-atlas.html#D22) | 2 / 5 | dialog | [Full spec](pages/D22.md) |
| [D23 Earnings](page-atlas.html#D23) | 3 / 6 | finance | [Full spec](pages/D23.md) |
| [D24 Earning / trip detail](page-atlas.html#D24) | 2 / 6 | detail | [Full spec](pages/D24.md) |
| [D25 Work history](page-atlas.html#D25) | 2 / 3 | list | [Full spec](pages/D25.md) |
| [D26 Upcoming commitments](page-atlas.html#D26) | 1 / 2 | list | [Full spec](pages/D26.md) |
| [D27 Commitment detail / handoff](page-atlas.html#D27) | 4 / 9 | timeline | [Full spec](pages/D27.md) |
| [D28 Driver account](page-atlas.html#D28) | 2 / 11 | settings | [Full spec](pages/D28.md) |
| [D29 Vehicles](page-atlas.html#D29) | 2 / 3 | list | [Full spec](pages/D29.md) |
| [D30 Vehicle registration / detail](page-atlas.html#D30) | 2 / 8 | form | [Full spec](pages/D30.md) |
| [D31 Driver inbox](page-atlas.html#D31) | 1 / 3 | list | [Full spec](pages/D31.md) |
| [D32 Driver Help / own case](page-atlas.html#D32) | 2 / 5 | form | [Full spec](pages/D32.md) |
| [D33 Driver safety / coordination](page-atlas.html#D33) | 3 / 3 | choice | [Full spec](pages/D33.md) |
| [D34 Scheduled-offer preferences](page-atlas.html#D34) | 2 / 3 | settings | [Full spec](pages/D34.md) |
| [D35 Cooperative membership](page-atlas.html#D35) | 1 / 4 | detail | [Full spec](pages/D35.md) |
| [D36 Professional credentials](page-atlas.html#D36) | 2 / 4 | list | [Full spec](pages/D36.md) |
| [D37 Vehicle deactivation review](page-atlas.html#D37) | 2 / 4 | dialog | [Full spec](pages/D37.md) |
| [D38 Online city/service choice](page-atlas.html#D38) | 2 / 4 | choice | [Full spec](pages/D38.md) |
| [D39 Driver safety report history](page-atlas.html#D39) | 2 / 3 | list | [Full spec](pages/D39.md) |
| [D40 Driver safety report creation](page-atlas.html#D40) | 2 / 4 | form | [Full spec](pages/D40.md) |
| [D41 Immediate fixed-route offer](page-atlas.html#D41) | 4 / 7 | offer | [Full spec](pages/D41.md) |
| [L00 Auth-method chooser / OTP phone entry](page-atlas.html#L00) | 2 / 3 | auth | [Full spec](pages/L00.md) |
| [L01 OTP verification / resend](page-atlas.html#L01) | 2 / 3 | auth | [Full spec](pages/L01.md) |
| [L02 Saved Home/Work / saved-place editor](page-atlas.html#L02) | 3 / 3 | form | [Full spec](pages/L02.md) |
| [L03 Service-category chooser](page-atlas.html#L03) | 2 / 2 | choice | [Full spec](pages/L03.md) |
| [L04 Card checkout / wallet / payout](page-atlas.html#L04) | 2 / 4 | handoff | [Full spec](pages/L04.md) |
| [L05 Continuous tracking / live trip sharing](page-atlas.html#L05) | 3 / 3 | map-share | [Full spec](pages/L05.md) |
| [L06 Contact verification / account export-delete](page-atlas.html#L06) | 2 / 4 | settings | [Full spec](pages/L06.md) |
| [L07 General messaging / masked calls / emergency integration](page-atlas.html#L07) | 2 / 3 | communication | [Full spec](pages/L07.md) |
| [L08 Cooperative governance/voting](page-atlas.html#L08) | 2 / 3 | governance | [Full spec](pages/L08.md) |
| [A00 Welcome](page-atlas.html#A00) | 2 / 4 | applicant-welcome | [Full spec](pages/A00.md) |
| [A01 Sign in](page-atlas.html#A01) | 1 / 2 | applicant-auth | [Full spec](pages/A01.md) |
| [A02 Registration](page-atlas.html#A02) | 1 / 4 | applicant-form | [Full spec](pages/A02.md) |
| [A03 City/application list](page-atlas.html#A03) | 2 / 2 | applicant-list | [Full spec](pages/A03.md) |
| [A04 Application overview](page-atlas.html#A04) | 2 / 4 | applicant-checklist | [Full spec](pages/A04.md) |
| [A05 Identity/credential step](page-atlas.html#A05) | 2 / 4 | applicant-form | [Full spec](pages/A05.md) |
| [A06 Evidence/document step](page-atlas.html#A06) | 2 / 3 | applicant-documents | [Full spec](pages/A06.md) |
| [A07 Vehicle step](page-atlas.html#A07) | 1 / 7 | applicant-form | [Full spec](pages/A07.md) |
| [A08 Review/submit](page-atlas.html#A08) | 2 / 5 | applicant-review | [Full spec](pages/A08.md) |
| [A09 Status/timeline](page-atlas.html#A09) | 3 / 6 | applicant-timeline | [Full spec](pages/A09.md) |
| [A10 More information/replacement](page-atlas.html#A10) | 3 / 3 | applicant-form | [Full spec](pages/A10.md) |
| [A11 Withdrawal review](page-atlas.html#A11) | 2 / 4 | applicant-dialog | [Full spec](pages/A11.md) |
| [A12 Account/language/style/sign out](page-atlas.html#A12) | 4 / 4 | applicant-settings | [Full spec](pages/A12.md) |
| [O00 Sign in](page-atlas.html#O00) | 1 / 2 | ops-auth | [Full spec](pages/O00.md) |
| [O01 MFA verification](page-atlas.html#O01) | 2 / 2 | ops-auth | [Full spec](pages/O01.md) |
| [O02 Step-up review](page-atlas.html#O02) | 2 / 3 | ops-dialog | [Full spec](pages/O02.md) |
| [O03 Scope picker](page-atlas.html#O03) | 2 / 4 | ops-choice | [Full spec](pages/O03.md) |
| [O04 Access/session gate](page-atlas.html#O04) | 1 / 2 | ops-gate | [Full spec](pages/O04.md) |
| [O05 Rollout overview](page-atlas.html#O05) | 3 / 5 | ops-overview | [Full spec](pages/O05.md) |
| [O06 Cities](page-atlas.html#O06) | 2 / 5 | ops-table | [Full spec](pages/O06.md) |
| [O07 City creation](page-atlas.html#O07) | 2 / 7 | ops-form | [Full spec](pages/O07.md) |
| [O08 Service-area versions](page-atlas.html#O08) | 3 / 4 | ops-map-list | [Full spec](pages/O08.md) |
| [O09 Service-area review](page-atlas.html#O09) | 3 / 5 | ops-review | [Full spec](pages/O09.md) |
| [O10 Configuration assembly](page-atlas.html#O10) | 3 / 8 | ops-form | [Full spec](pages/O10.md) |
| [O11 Configuration review/activation](page-atlas.html#O11) | 3 / 8 | ops-review | [Full spec](pages/O11.md) |
| [O12 Readiness evidence](page-atlas.html#O12) | 3 / 6 | ops-checklist | [Full spec](pages/O12.md) |
| [O13 City lifecycle review](page-atlas.html#O13) | 2 / 5 | ops-dialog | [Full spec](pages/O13.md) |
| [O14 Operators](page-atlas.html#O14) | 2 / 4 | ops-table | [Full spec](pages/O14.md) |
| [O15 Operator creation/edit](page-atlas.html#O15) | 1 / 4 | ops-form | [Full spec](pages/O15.md) |
| [O16 Operator status/assignment review](page-atlas.html#O16) | 2 / 4 | ops-dialog | [Full spec](pages/O16.md) |
| [O17 Tariffs](page-atlas.html#O17) | 2 / 4 | ops-table | [Full spec](pages/O17.md) |
| [O18 Tariff editor/review](page-atlas.html#O18) | 1 / 7 | ops-form | [Full spec](pages/O18.md) |
| [O19 Operator fees](page-atlas.html#O19) | 2 / 3 | ops-table | [Full spec](pages/O19.md) |
| [O20 Fee editor/review](page-atlas.html#O20) | 1 / 12 | ops-form | [Full spec](pages/O20.md) |
| [O21 Scheduling policy](page-atlas.html#O21) | 2 / 4 | ops-table | [Full spec](pages/O21.md) |
| [O22 Scheduling editor/review](page-atlas.html#O22) | 3 / 21 | ops-form | [Full spec](pages/O22.md) |
| [O23 Fixed-route catalogue](page-atlas.html#O23) | 2 / 3 | ops-table | [Full spec](pages/O23.md) |
| [O24 Route identity editor](page-atlas.html#O24) | 1 / 8 | ops-form | [Full spec](pages/O24.md) |
| [O25 Route version/direction/stop editor](page-atlas.html#O25) | 4 / 12 | ops-map-form | [Full spec](pages/O25.md) |
| [O26 Route publication/replacement review](page-atlas.html#O26) | 3 / 6 | ops-review | [Full spec](pages/O26.md) |
| [O27 Staff access](page-atlas.html#O27) | 2 / 3 | ops-table | [Full spec](pages/O27.md) |
| [O28 Grant request](page-atlas.html#O28) | 2 / 6 | ops-form | [Full spec](pages/O28.md) |
| [O29 Revoke request](page-atlas.html#O29) | 2 / 5 | ops-dialog | [Full spec](pages/O29.md) |
| [O30 Independent grant decision](page-atlas.html#O30) | 2 / 7 | ops-dialog | [Full spec](pages/O30.md) |
| [O31 Recruitment queue](page-atlas.html#O31) | 3 / 4 | ops-master-detail | [Full spec](pages/O31.md) |
| [O32 Requirement versions](page-atlas.html#O32) | 2 / 3 | ops-table | [Full spec](pages/O32.md) |
| [O33 Requirement editor/review](page-atlas.html#O33) | 5 / 19 | ops-form | [Full spec](pages/O33.md) |
| [O34 Application review](page-atlas.html#O34) | 3 / 6 | ops-master-detail | [Full spec](pages/O34.md) |
| [O35 Driver decision review](page-atlas.html#O35) | 3 / 9 | ops-review | [Full spec](pages/O35.md) |
| [O36 Protected-document retrieval](page-atlas.html#O36) | 2 / 5 | ops-document | [Full spec](pages/O36.md) |
| [O37 Payment overview](page-atlas.html#O37) | 1 / 4 | ops-overview | [Full spec](pages/O37.md) |
| [O38 Recipient list/create](page-atlas.html#O38) | 2 / 3 | ops-table | [Full spec](pages/O38.md) |
| [O39 Capability list/create](page-atlas.html#O39) | 2 / 3 | ops-table | [Full spec](pages/O39.md) |
| [O40 Transfer queue/detail](page-atlas.html#O40) | 2 / 5 | ops-master-detail | [Full spec](pages/O40.md) |
| [O41 Transfer decision review](page-atlas.html#O41) | 2 / 6 | ops-dialog | [Full spec](pages/O41.md) |
| [O42 Refund recorder/review](page-atlas.html#O42) | 2 / 7 | ops-form | [Full spec](pages/O42.md) |
| [O43 Refund ledger/detail](page-atlas.html#O43) | 2 / 4 | ops-table | [Full spec](pages/O43.md) |
| [O44 Scheduled exceptions](page-atlas.html#O44) | 2 / 5 | ops-master-detail | [Full spec](pages/O44.md) |
| [O45 Intelligence overview](page-atlas.html#O45) | 4 / 6 | ops-charts | [Full spec](pages/O45.md) |
| [O46 Aggregate report detail](page-atlas.html#O46) | 3 / 6 | ops-report | [Full spec](pages/O46.md) |
| [O47 Support/safety queues](page-atlas.html#O47) | 3 / 3 | ops-master-detail | [Full spec](pages/O47.md) |
| [O48 Case detail/timeline](page-atlas.html#O48) | 3 / 6 | ops-detail | [Full spec](pages/O48.md) |
| [O49 Support triage/transition](page-atlas.html#O49) | 2 / 5 | ops-dialog | [Full spec](pages/O49.md) |
| [O50 Safety handoff/transition](page-atlas.html#O50) | 3 / 4 | ops-dialog | [Full spec](pages/O50.md) |
| [O51 Overdue alert acknowledgement](page-atlas.html#O51) | 2 / 4 | ops-dialog | [Full spec](pages/O51.md) |
| [O52 Retention/legal hold](page-atlas.html#O52) | 2 / 2 | ops-table | [Full spec](pages/O52.md) |
| [O53 Account security](page-atlas.html#O53) | 2 / 7 | ops-form | [Full spec](pages/O53.md) |
| [O54 Account-security command review](page-atlas.html#O54) | 3 / 5 | ops-dialog | [Full spec](pages/O54.md) |
| [O55 Incident queue/create](page-atlas.html#O55) | 2 / 8 | ops-form-list | [Full spec](pages/O55.md) |
| [O56 Incident detail/responsibility](page-atlas.html#O56) | 3 / 9 | ops-detail | [Full spec](pages/O56.md) |
| [O57 Incident timeline/event](page-atlas.html#O57) | 2 / 7 | ops-form | [Full spec](pages/O57.md) |
| [O58 Incident transition/recovery](page-atlas.html#O58) | 2 / 7 | ops-dialog | [Full spec](pages/O58.md) |
| [O59 Postmortem](page-atlas.html#O59) | 2 / 8 | ops-form | [Full spec](pages/O59.md) |
| [O60 Audit](page-atlas.html#O60) | 2 / 4 | ops-audit | [Full spec](pages/O60.md) |
| [O61 Restricted/empty/error detail](page-atlas.html#O61) | 2 / 4 | ops-gate | [Full spec](pages/O61.md) |
| [O62 City driver authorization detail](page-atlas.html#O62) | 2 / 7 | ops-detail | [Full spec](pages/O62.md) |
| [O63 City authorization suspension](page-atlas.html#O63) | 2 / 5 | ops-dialog | [Full spec](pages/O63.md) |
| [O64 City authorization revocation](page-atlas.html#O64) | 2 / 5 | ops-dialog | [Full spec](pages/O64.md) |
| [O65 City authorization reinstatement](page-atlas.html#O65) | 2 / 5 | ops-dialog | [Full spec](pages/O65.md) |
| [O66 City-service assignment creation](page-atlas.html#O66) | 3 / 6 | ops-form | [Full spec](pages/O66.md) |
| [O67 Service-area boundary editor](page-atlas.html#O67) | 3 / 8 | ops-map-form | [Full spec](pages/O67.md) |
| [O68 Recipient lifecycle review](page-atlas.html#O68) | 2 / 5 | ops-dialog | [Full spec](pages/O68.md) |
| [O69 Payment-capability lifecycle review](page-atlas.html#O69) | 2 / 6 | ops-dialog | [Full spec](pages/O69.md) |
| [O70 Operations MFA recovery-code mode](page-atlas.html#O70) | 2 / 2 | ops-auth | [Full spec](pages/O70.md) |
| [O71 Safety case detail](page-atlas.html#O71) | 3 / 6 | ops-detail | [Full spec](pages/O71.md) |
| [O72 Retention review detail](page-atlas.html#O72) | 1 / 4 | ops-detail | [Full spec](pages/O72.md) |
| [O73 Legal-hold placement review](page-atlas.html#O73) | 2 / 4 | ops-dialog | [Full spec](pages/O73.md) |
| [O74 Legal-hold release review](page-atlas.html#O74) | 2 / 4 | ops-dialog | [Full spec](pages/O74.md) |
| [O75 Overdue alert detail](page-atlas.html#O75) | 2 / 5 | ops-detail | [Full spec](pages/O75.md) |
| [O76 Recipient creation](page-atlas.html#O76) | 2 / 5 | ops-form | [Full spec](pages/O76.md) |
| [O77 Payment-capability creation](page-atlas.html#O77) | 2 / 6 | ops-form | [Full spec](pages/O77.md) |
| [O78 Requirement-version lifecycle review](page-atlas.html#O78) | 2 / 4 | ops-dialog | [Full spec](pages/O78.md) |
| [O79 Tariff lifecycle review](page-atlas.html#O79) | 2 / 5 | ops-dialog | [Full spec](pages/O79.md) |
| [O80 Fee-policy lifecycle review](page-atlas.html#O80) | 2 / 5 | ops-dialog | [Full spec](pages/O80.md) |
| [O81 Scheduling-policy lifecycle review](page-atlas.html#O81) | 2 / 5 | ops-dialog | [Full spec](pages/O81.md) |
| [O82 Route replacement review](page-atlas.html#O82) | 3 / 5 | ops-dialog | [Full spec](pages/O82.md) |
| [O83 Route retirement review](page-atlas.html#O83) | 2 / 4 | ops-dialog | [Full spec](pages/O83.md) |
| [O84 Support triage](page-atlas.html#O84) | 2 / 5 | ops-dialog | [Full spec](pages/O84.md) |
| [O85 Safety transition review](page-atlas.html#O85) | 2 / 5 | ops-dialog | [Full spec](pages/O85.md) |
| [O86 Selected city detail](page-atlas.html#O86) | 3 / 12 | ops-detail | [Full spec](pages/O86.md) |
| [O87 Readiness decision review](page-atlas.html#O87) | 3 / 6 | ops-dialog | [Full spec](pages/O87.md) |
