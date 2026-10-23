"""Auditable documentation inventory, not a route/test completion claim."""
from pathlib import Path
from datetime import UTC, datetime
import re,json,hashlib
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent.parent
areas=['TaxiMobile/shared/src/commonMain','TaxiMobile/shared/src/androidMain','TaxiMobile/shared/src/iosMain','TaxiMobile/webApp/src/webMain']
pages=json.loads((ROOT/'atlas-data.json').read_text(encoding='utf8'))
rows=[];files=[]
component_files={'TaxiEntryFrame':'C39','TaxiStyleChooser':'C04','TaxiButton':'C01','MapFab':'C02','TaxiTextField':'C03','SpecializedFields':'C03 C04','TaxiSegmentedControl':'C05','MapToolbar':'C06','TaxiSheet':'C08','FareBlock':'C11','DriverCard':'C12','OfferCard':'C13','StatusPill':'C17','ToastBanner':'C18','Skeleton':'C19','ConfirmDialog':'C22','SuccessConfirmation':'C18','TaxiCards':'C25','OptionalArtwork':'C39','TaxiArtwork':'C39','MapLibreTripMap':'C10 C16','OperationsComponents':'C17 C18 C30 C31 C32 C39','ApplicantComponents':'C01 C17 C18 C23'}
exact={
'AccountSecuritySection':'S14 S15 S16 S17 S18 S19',
'NotificationInboxSection':'R32 D31','SupportTicketSection':'R34 R35 D32','SafetyReportSection':'R39 R40 D39 D40',
'SessionLoadingScreen':'S00','WelcomeContent':'S02','SignedOutContent':'S03 S04 S05 S06 S07','DriverApplicationRequiredScreen':'D00 D01','DriverApplicationPendingScreen':'D06','OfflineScreen':'S09','UpgradeRequiredScreen':'S01',
'PassengerRideSheet':'R00 R01 R02 R03 R05 R06 R07 R08 R09 R10 R11 R12 R13 R14 R15 R16 R17',
'PassengerScheduledSheet':'R26 R27 R28 R29','ScheduledCancellationTerms':'R27 R29',
'PassengerFixedRoutesSheet':'R24','FixedRouteDirectionCard':'R25','RecentDestinationSection':'R38','CoordinateFields':'R42','PlaceDiscoverySection':'R04',
'PassengerAccountSheet':'R30 S14 S15 S16 S17 S18 S19','PassengerProfileSection':'R31','PassengerHistorySection':'R22','PassengerHistoryDetail':'R23','PassengerReceipt':'R18','ManualTransferReceipt':'R19','RefundReceiptSummary':'R20','PassengerRatingSection':'R21','PassengerInboxSheet':'R32','PassengerSafetySheet':'R36',
'DriverOperationsSheet':'D10 D12 D13 D15 D16 D17 D18 D19 D20 D38 D41','DriverScheduledSheet':'D14 D26 D27 D34','TimedOfferCard':'D13 D14 D41','DriverCompletionControls':'D19 D20','PendingCashPaymentsSection':'D21 D22','DriverHistoryDetail':'D24','DriverEarningCard':'D23 D24','DriverVehicleSection':'D29 D30 D37','DriverAccountSheet':'D28 D35 D36 S14 S15 S16 S17 S18 S19','DriverInboxSheet':'D31','DriverSafetySheet':'D33','DriverToolbar':'D11',
'RecruitingCities':'D01','ApplicationDetail':'D00 D05 D06','RequirementEditor':'D02 D03','EvidenceChoices':'D03','ApplicantVehicleForm':'D04','ApplicationTimeline':'D06','CityAuthorizationSummary':'D07','LatestRideCoordinationSection':'R37 D33','RideCoordinationActions':'R37 D33',
'CreateCityDialog':'O07','CreateOperatorDialog':'O15','CreateAssignmentDialog':'O66','CreateServiceAreaDialog':'O67','CreateConfigurationDialog':'O10','ControlPlaneReviewDialog':'O09 O11 O16',
'RolloutOverview':'O05','CitiesScreen':'O06','CityDetail':'O86','ReadinessGateGroup':'O12','ReadinessReviewDialog':'O87','OperatorsScreen':'O14','AuditScreen':'O60','LifecycleReviewDialog':'O13',
'TariffEditor':'O18','OperatorFeeEditor':'O20','SchedulingPolicyEditor':'O22','TariffSection':'O17','OperatorFeeSection':'O19','SchedulingPolicySection':'O21','PolicyTransitionDialog':'O79 O80 O81',
'RecipientCreator':'O76','RecipientList':'O38 O68','CapabilityCreator':'O77','CapabilityList':'O39 O69','CapabilityRow':'O69','TransferQueue':'O40 O41','RefundRecorder':'O42','RefundHistory':'O43',
'RouteIdentityEditor':'O24','RouteVersionEditor':'O25','RouteCommandDialog':'O26 O82 O83','FixedRouteCard':'O23','GeometryPreview':'O25',
'CreateGrantRequest':'O28','RevokeGrantRequest':'O29','GrantDecisionDialog':'O30',
'RequirementVersionSection':'O32','RequirementVersionEditor':'O33','RequirementItemEditor':'O33','RequirementTransitionDialog':'O78','DriverReviewSection':'O31','DriverApplicationReview':'O34 O36 O62','DriverDecisionForm':'O35',
'CityAuthorizationReview':'O62 O63 O64 O65',
'SupportQueueSection':'O47','SafetyQueueSection':'O47','OverdueAlertsSection':'O75','RetentionSection':'O52 O72','SupportCaseDetailDialog':'O48','SupportCaseFlow':'O48 O49 O50 O84','SafetyCaseFlow':'O71 O85','SupportTriageDialog':'O84','SupportTransitionDialog':'O49','SafetyHandoffDialog':'O50','SafetyTransitionDialog':'O85','AlertAckDialog':'O51','LegalHoldDialog':'O73 O74',
'CreateIncidentPanel':'O55','IncidentQueue':'O55','IncidentDetail':'O56','ResponsibilitiesPanel':'O56','TimelinePanel':'O57','TransitionPanel':'O58','IncidentPostmortemPanel':'O59',
'LoginScreen':'O00','LoginCard':'O00','MfaVerificationScreen':'O01 O70','MfaStepUpDialog':'O02','ScopeTopBar':'O03','InitialLoading':'O04','LoadFailure':'O04',
'AnalyticsScreen':'O45 O46','ScheduledExceptionsScreen':'O44','AccountSecurityScreen':'O53 O54',
'ApplicantWelcome':'A00','ApplicantAuthenticationPanel':'A01 A02','ApplicantDashboard':'A03 A12','ApplicantApplicationEditor':'A04 A05 A06 A07 A08 A09 A10 A11',
}
exact.update({'DriverRideHistoryDetail':'D24','PassengerRideHistoryDetail':'R23','RideRatingSection':'R21','ApplicantRequirementEditor':'A05 A06','CaseDetailBody':'O48 O71','AlertAcknowledgementDialog':'O51','ControlPlaneConfirmDialog':'O09 O11 O16','OnboardingAggregateSection':'O31','RolloutScreen':'O05','FeePolicyEditor':'O20','CreateSecurityIncidentPanel':'O55','IncidentResponsibilitiesPanel':'O56','IncidentTransitionPanel':'O58','CreateAdministrativeGrantDialog':'O28','RevokeAdministrativeGrantDialog':'O29','AdministrativeGrantDecisionDialog':'O30'})
wrappers={'CommandDialog':'C22','EditorDialog':'C23','EditorField':'C03','ScreenColumn':'C32','OperationsPanel':'C23','PolicyEditorFrame':'C33','SecurityIncidentPanel':'C23'}
containers={'TaxiMobileScreen','PassengerHome','DriverHome','DriverOnboardingScreen','OperationsApp','OperationsShell','OperationsWorkspace','ApplicantPortalApp','ApplicantWelcomePanel','PricingEconomicsScreen','PaymentOperationsScreen','DriverRecruitmentScreen','FixedRoutesScreen','StaffAccessScreen','CaseOperationsScreen','SecurityIncidentScreen','App','PassengerToolbar','GatePage','LoginBrandPanel','OperationsSidebar','CompactNavigation','SidebarDestination','ApplicantAuthenticationPanel'}
for area in areas:
 for path in sorted((REPO/area).rglob('*.kt')):
  src=path.read_text(encoding='utf8')
  if '@Composable' not in src:continue
  rel=path.relative_to(REPO).as_posix()
  ids=[p['id'] for p in pages if p['source']==rel]
  files.append({'source':rel,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pageIds':ids})
  pattern=r'@Composable\s+(?:(?:private|internal|public|expect|actual|inline|suspend)\s+)*fun\s+(?:<[^>]+>\s+)?([\w.]+)\s*\('
  for m in re.finditer(pattern,src):
   qualified=m[1];name=qualified.split('.')[-1];links=exact.get(name,'').split()
   if 'applicant/' in rel:
    links={'RequirementEditor':['A05'],'EvidenceChoices':['A06'],'ApplicantVehicleForm':['A07'],'ApplicationTimeline':['A09']}.get(name,links)
    if name in {'WelcomePanel','AuthenticationPanel','Dashboard'}:links={'WelcomePanel':['A00'],'AuthenticationPanel':['A01','A02'],'Dashboard':['A03','A12']}[name]
   comp=wrappers.get(name,'').split() or next((v.split() for k,v in component_files.items() if path.name.startswith(k)),[])
   kind='page/detail/editor' if links else 'shared component' if comp else 'composition shell' if name in containers else 'presentation helper'
   refs=links or comp or (ids if kind=='composition shell' else [])
   rows.append({'source':rel,'line':src[:m.start()].count('\n')+1,'function':qualified,'classification':kind,'designRefs':refs})
unresolved=[r for r in rows if r['classification']=='presentation helper' and any(v in r['function'] for v in ['Screen','Dialog','Editor','Panel','Detail','Sheet','Section'])]
(ROOT/'source-ui-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ROOT/'source-ui-files.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
lines=['# Source coverage audit','',f'Prepared from the actual checkout on {datetime.now(UTC).date().isoformat()}. This inventories shared mobile, Android/iOS map presentation and applicant/operations Compose declarations. A composable is not automatically a page; reusable components, shells and presentation helpers are classified separately. Proposed splits and future capability views remain design surfaces, not implemented routes.','','[Open every page](page-atlas.html). [Machine inventory](source-ui-inventory.json). [Source-file hashes](source-ui-files.json).','','## Reconciliation','','New source-backed views added after the owner challenged representative-screen coverage: active sessions, password changes, recovery custody, recent destinations, safety history/create, city selection, driver scheduling preferences, membership, credentials, vehicle deactivation, immediate fixed-route offers, authorization actions, assignment/boundary editors, recipient/capability creation and lifecycle reviews, MFA saved-code mode, restricted safety detail, retention/holds, overdue alert detail, policy/route lifecycle reviews, separate support triage, selected city detail and readiness review.','','Corrected unsupported account search, recipient pause/activate, arbitrary support assignee/category, invented operator identity field and requirement-wide service selector. Fee/scheduling, recruitment and refund editors now carry source-controlled fields and choices.','','## Inventory method and limits','','Scan named `@Composable` functions, preserving extension receiver and function name; include platform map functions. Inline composable lambdas and runtime navigation outcomes need their parent screen audit, not artificial page counts. Per-file source anchors are inspection pointers; they do not prove native visual acceptance. Page-specific control/behavior review and actual Compose renders remain mandatory after approval.','','## Declarations','','| Source declaration | Kind | Planned surfaces/components |','| --- | --- | --- |']
for r in rows:
 refs='; '.join(f'[{v}](page-atlas.html#{v})' if v[0]!='C' else f'[{v}](components.md)' for v in r['designRefs']) or 'Inherits parent layout/state; no separate navigation surface'
 lines.append(f"| `{r['source']}:{r['line']}` · `{r['function']}` | {r['classification']} | {refs} |")
lines += ['','## Page-by-page artifact ledger','','| View | Blocks / content-control items | Composition | Specification |','| --- | --- | --- | --- |']
for p in pages:lines.append(f"| [{p['id']} {p['name']}](page-atlas.html#{p['id']}) | {len(p['blocks'])} / {sum(len(b['items']) for b in p['blocks'])} | {p['layout']} | [Full spec]({p['spec']}) |")
(ROOT/'coverage.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps({'sourceFiles':len(files),'declarations':len(rows),'unresolvedCandidates':unresolved},indent=2))
