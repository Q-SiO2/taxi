"""One-time authoring refinements; run before rebuilding documentation."""
from pathlib import Path
root=Path(__file__).resolve().parent
path=root/'atlas_content.py'
s=path.read_text(encoding='utf8')
changes={
"Role template~City manager~choice~Actual permitted templates":"Role template~City manager~choice~Scope derives from the selected role; server-owned templates~Platform admin;Operator admin;City manager;Driver reviewer;Pricing manager;Payment reconciler;Support agent",
"Severity~SEV2~choice~Actual enum":"Severity~SEV2 · high~choice~~SEV1 · critical;SEV2 · high;SEV3 · moderate;SEV4 · low",
"Category~Account compromise~choice~Actual enum":"Category~Account compromise~choice~~Account compromise;Provider credential exposure;Data exposure;Malicious access;Service abuse;Other reviewed security event",
"Scope~Selected city or whole market~choice":"Scope~Selected city~choice~~Selected city;Whole market",
"Role~Actual supported responsibility role~choice":"Role~Security response lead~choice~~Security response lead;Communications lead;Operations liaison;Postmortem owner",
"Kind~Actual event enum~choice":"Kind~Evidence linked~choice~~Evidence linked;Containment action;Communication decision;Recovery action;Postmortem action",
"Evidence/reference~~text~Actual permitted non-secret reference":"Scoped audit UUID~~text~Optional authorized exact UUID','External runbook/reference~~text~Optional non-secret reference",
"'Conclusion~~textarea~Bounded factual summary','Completed at~~datetime~ISO UTC'":"'Outcome~Control changed~choice~~Control changed;Follow-up required;No further action','Conclusion~~textarea~10–500 factual characters; no secrets','Completed at~~datetime~ISO UTC','Scoped audit UUID~~text~Optional authorized UUID','Postmortem / follow-up reference~~text~Required for Follow-up required; otherwise optional'",
"Evidence type~Actual permitted type~choice~Choices and compatible validity rules in source contract appendix":"Evidence type~PROFILE~choice~Changing type resets compatible default validity~PROFILE;VEHICLE;CREDENTIAL;DOCUMENT;BOOLEAN;DATE;TEXT",
"Validity rule~Compatible rule for selected evidence~choice":"Validity rule~PROFILE_OWNED~choice~PROFILE: PROFILE_OWNED. VEHICLE: OWNED/VERIFIED. CREDENTIAL: OWNED/VERIFIED/UNEXPIRED. DOCUMENT: SCANNED_CLEAN. BOOLEAN: TRUE. DATE: NOT_FUTURE. TEXT: PRESENT. Only compatible prefixed code is selectable",
}
for old,new in changes.items():
 if old not in s:raise SystemExit('Missing authoring text: '+old)
 s=s.replace(old,new)
path.write_text(s,encoding='utf8')
path=root/'audit_source.py';s=path.read_text(encoding='utf8');s=s.replace("containers={'TaxiMobileScreen'", "exact.update({'DriverRideHistoryDetail':'D24','PassengerRideHistoryDetail':'R23','RideRatingSection':'R21','ApplicantRequirementEditor':'A05 A06','CaseDetailBody':'O48 O71','AlertAcknowledgementDialog':'O51','ControlPlaneConfirmDialog':'O09 O11 O16','OnboardingAggregateSection':'O31','RolloutScreen':'O05','FeePolicyEditor':'O20','CreateSecurityIncidentPanel':'O55','IncidentResponsibilitiesPanel':'O56','IncidentTransitionPanel':'O58','CreateAdministrativeGrantDialog':'O28','RevokeAdministrativeGrantDialog':'O29','AdministrativeGrantDecisionDialog':'O30'})\nwrappers={'CommandDialog':'C22','EditorDialog':'C23','EditorField':'C03','ScreenColumn':'C32','OperationsPanel':'C23','PolicyEditorFrame':'C33','SecurityIncidentPanel':'C23'}\ncontainers={'TaxiMobileScreen'")
s=s.replace("comp=next((v.split()", "comp=wrappers.get(name,'').split() or next((v.split()")
path.write_text(s,encoding='utf8')
path=root/'atlas-template.html';s=path.read_text(encoding='utf8');s=s.replace('minmax(min(100%,360px),1fr)))','minmax(min(100%,360px),1fr))').replace('minmax(min(100%,270px),1fr)))','minmax(min(100%,270px),1fr))')
s=s.replace("j===0&&kind!=='checkbox'", "(o===i.value||(!opts.includes(i.value)&&j===0))&&kind!=='checkbox'")
s=s.replace("'Restricted','Session expired'].includes(s);return", "'Restricted','Session expired','Expired offer'].includes(s);return")
s=s.replace("20 shared mobile, 43 passenger, 40 driver, 9 deferred capability, 13 applicant and 86 operations views", "${['Shared mobile','Passenger','Driver','Deferred capability','Applicant','Operations'].map(g=>PAGES.filter(p=>p.group===g).length+' '+g.toLowerCase()).join(', ')} views")
path.write_text(s,encoding='utf8')
print('Refined closed choice sets, complete incident fields, source aliases and responsive gallery.')
