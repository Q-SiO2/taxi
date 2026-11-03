"""Build the review-only atlas and individual page specifications.

This belongs to documentation, never application/runtime code. Its inputs are
the page books plus explicitly authored page compositions in atlas_content.py.
Every inventory row must have its own composition; no default screen fallback.
"""
from pathlib import Path
import hashlib
import json
import re
import runpy

ROOT = Path(__file__).resolve().parent


def page_book(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([SRDLAO]\d{2}) (.+?) \|", line)
        if not m:
            continue
        cells = [v.strip() for v in line.strip("|").split("|")]
        result[m[1]] = dict(id=m[1], name=m[2], composition=cells[1],
                            controls=cells[2], guardrails=cells[3] if len(cells)>3 else cells[2])
    return result


def main():
    pages = page_book(ROOT / "mobile-pages.md") | page_book(ROOT / "web-pages.md")
    authored = runpy.run_path(str(ROOT / "atlas_content.py"))["SCREENS"]
    expressive_file = ROOT / 'expressive-data.json'
    expression = json.loads(expressive_file.read_text(encoding='utf-8')) if expressive_file.exists() else {'pages':[], 'art':[]}
    placements = {p['id']:p for p in expression['pages']}
    artwork = {a['id']:a for a in expression['art']}
    missing, extra = sorted(pages.keys()-authored.keys()), sorted(authored.keys()-pages.keys())
    if missing or extra:
        raise SystemExit(f"Composition coverage failure: missing={missing}, extra={extra}")
    destination = ROOT / "pages"
    destination.mkdir(exist_ok=True)
    groups = {"S":"Shared mobile", "R":"Passenger", "D":"Driver", "L":"Deferred capability",
              "A":"Applicant", "O":"Operations"}
    output = []
    for key in sorted(pages, key=lambda x: (list(groups).index(x[0]), int(x[1:]))):
        p = pages[key] | authored[key]
        p["group"] = groups[key[0]]
        p["deferred"] = key.startswith("L") or key == "R04"
        p["source"] = source_for(key)
        p["states"] = states_for(p)
        expressive_ids={'S02','R00','R22','R24','R30','R32','R33','D00','D10','D23','D25','D28','D31','D32','A00','A03','A04'}
        p['styleProfile']={'styles':['folded_streets','street_press','glazed_machine','notepad'],
                           'expressiveContext':'bounded entry framing' if key in expressive_ids else 'static functional framing',
                           'notepad':'grayscale ruled utility; icons and main workflow retained; no decorative animation',
                           'mainIllustration':False}
        if key in placements:
            p['expression'] = placements[key]
            p['expressionSvg'] = artwork[p['expression']['asset']]['svg'] if p['expression']['asset'] else None
        if not p.get("blocks") or not p.get("actions") or not p.get("title"):
            raise SystemExit(f"Incomplete composition {key}")
        text = markdown_for(p)
        (destination / f"{key}.md").write_text(text, encoding="utf-8")
        p["spec"] = f"pages/{key}.md"
        p["specSha256"] = hashlib.sha256((destination / f"{key}.md").read_bytes()).hexdigest()
        output.append(p)
    (ROOT / "atlas-data.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    style_rows=[{'id':p['id'],'name':p['name'],'group':p['group'],**p['styleProfile']} for p in output]
    (ROOT/'style-coverage.json').write_text(json.dumps(style_rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    ledger=['# Four-style page coverage','', '**Selected system — 15 October 2026.** All 213 source-derived design views use the same four-style contract. This is browser/specification coverage, not native acceptance.', '', 'See [style-options.md](style-options.md). Bounded entry framing means one optional expressive performance outside stable content; static functional framing keeps task facts, controls and dense/review work steady. Notepad never starts a decorative controller.', '', '| Page | Name | Expressive styles: Folded Streets / Street Press / Glazed Machine | Notepad | Specification |', '| --- | --- | --- | --- | --- |']
    ledger += [f"| {p['id']} | {p['name']} | {p['styleProfile']['expressiveContext']} | Grayscale; icons/tasks retained; no decorative motion | [Full view]({p['spec']}) |" for p in output]
    (ROOT/'style-coverage.md').write_text('\n'.join(ledger)+'\n',encoding='utf-8')
    manifest = {"pages":len(output),"groups":{g:sum(p["group"]==g for p in output) for g in groups.values()},
                "uniqueCompositions":len({json.dumps(p["blocks"],sort_keys=True) for p in output}),
                "sourceInputs":[{"file":f,"sha256":hashlib.sha256((ROOT/f).read_bytes()).hexdigest()}
                                for f in ["mobile-pages.md","web-pages.md","atlas_content.py"]]}
    if manifest['uniqueCompositions'] != len(output):
        raise SystemExit('Duplicate full compositions: review authoring before publication')
    (ROOT / "atlas-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    template = (ROOT / "atlas-template.html").read_text(encoding="utf-8")
    payload = json.dumps(output,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")
    (ROOT / "page-atlas.html").write_text(template.replace("__PAGE_DATA__",payload),encoding="utf-8")
    print(json.dumps(manifest))


def source_for(key):
    base="TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/"
    web="TaxiMobile/webApp/src/webMain/kotlin/org/example/taximobile/"
    n=int(key[1:])
    if key.startswith("S"):
        return base+("account/AccountSecuritySection.kt" if n>=14 else "app/TaxiMobileScreen.kt")
    if key.startswith("R"):
        if n==4: return base+"passenger/PlaceDiscoverySection.kt"
        if n in {34,35,36,39,40}: return base+"app/SharedSections.kt"
        if n==37: return base+"rides/RideCoordinationSection.kt"
        return base+"passenger/PassengerHome.kt"
    if key.startswith("D"):
        if n in {21,22}: return base+"driver/PendingCashPaymentsSection.kt"
        if n<=6: return base+"driver/onboarding/DriverOnboardingScreen.kt"
        if n in {39,40}: return base+"app/SharedSections.kt"
        return base+"driver/DriverHome.kt"
    if key.startswith("A"):
        return web+"applicant/ui/"+("ApplicantPortalApp.kt" if n in {0,1,2,3,12} else "ApplicantApplicationEditor.kt")
    if key.startswith("L"): return "docs/extended_ui.md (future design; capability not delivered)"
    if n<=4 or n==70: file="OperationsApp.kt"
    elif n in {7,8,10,11,13,15,16,66,67}: file="ControlPlaneEditors.kt"
    elif 17<=n<=22: file="PricingEconomicsEditors.kt" if n%2==0 else "PricingEconomicsScreen.kt"
    elif 23<=n<=26: file="FixedRoutesScreen.kt"
    elif 27<=n<=30: file="StaffAccessScreen.kt"
    elif 31<=n<=36: file="DriverRecruitmentScreen.kt"
    elif 37<=n<=43 or n in {68,69,76,77}: file="PaymentOperationsScreen.kt"
    elif n==44: file="ScheduledExceptionsScreen.kt"
    elif n in {45,46}: file="AnalyticsScreen.kt"
    elif n in {53,54}: file="AccountSecurityScreen.kt"
    elif 55<=n<=59: file="SecurityIncidentScreen.kt"
    elif 62<=n<=65: file="CityAuthorizationReview.kt"
    elif n in {47,48,49,50,51,52,71,72,73,74,75,84,85}: file="CaseOperationsScreen.kt"
    elif n==78: file="DriverRecruitmentScreen.kt"
    elif n in {79,80,81}: file="PricingEconomicsScreen.kt"
    elif n in {82,83}: file="FixedRoutesScreen.kt"
    else: file="OperationsScreens.kt"
    return web+"operations/ui/"+file


def states_for(p):
    rules={"Default":("Show the authored facts and controls in the proposed layout.","Actions are design specimens; they never call the API."),
           "Loading":("Reserve the shape of unknown content; retain known title, scope and navigation.","One loading announcement; no invented zero/empty values."),
           "Empty":("Replace this page's record area with its explicit empty explanation.","Never equate a failed/restricted query with zero records."),
           "Error":("Inline failure explanation beside the affected content/action; preserve safe draft.","Retry only the failed read or reconcile the actual write outcome."),
           "Offline":("Retain permitted last-confirmed context; add freshness and connection notice.","Disable unsafe writes; do not book, accept, authorize or settle locally."),
           "Stale":("Mark last-refresh/observation age; leave confirmed lifecycle facts legible.","Re-read before time-sensitive or authority-changing commands."),
           "Restricted":("Remove protected details/actions and explain the access/capability boundary.","A hidden control is not authorization; stale confidential detail is cleared."),
           "Busy":("Keep the initiating action's width and replace its label with specific progress text.","One write in flight; competing writes and duplicate submission disabled."),
           "Validation":("Error summary plus field-local message; focus the first invalid field.","Existing API constraints repeated; secrets never echoed in an error."),
           "Conflict":("Explain that the reviewed record/phase/version changed and reload it.","No silent overwrite, automatic replay, or local status correction."),
           "Unknown outcome":("Keep the submitted context and show that confirmation is unavailable.","Reconcile first; never manufacture success or duplicate a financial/request action."),
           "Session expired":("Remove protected state; preserve only safe navigation context for sign-in.","Credential clearing/session-generation fencing prevents stale restoration."),
           "Confirmed":("Render only the actual confirmed result appropriate to this page.","A static check cannot imply payment/assignment/eligibility beyond the response.")}
    rules['Rate limited']=("Show the actual retry window beside the affected command; retain safe draft.","No automatic resubmission or bypass; do not disclose account existence.")
    rules['Location denied']=("Keep this page's textual journey context; show permission/settings guidance and manual map-selection alternative where supported.","Driver availability remains gated by required fresh location; permission is never presumed.")
    rules['Map unavailable']=("Replace tiles with a neutral bounded map placeholder and keep the authored location/route text.","No false route or nearby supply; final request still needs actual points and current eligibility.")
    rules['Outside service area']=("Keep the selected point visible with an explicit unsupported-area explanation.","No quote/request/online claim for an ineligible point or city.")
    rules['Expired offer']=("Retain the offer summary with an expired label and refresh/return action.","Accept is unavailable; timers are derived from server time, never restarted by rendering.")
    rules['Payment pending']=("Keep the actual amount/method and prominent unconfirmed label.","Ride completion, passenger claim and locally checked controls cannot settle a payment.")
    rules['Capability unavailable']=("Explain the missing delivered capability and show the supported alternative.","No inactive control that appears to perform provider/payment/verification work.")
    types={i['type'] for b in p['blocks'] for i in b['items']}
    read=any(b['kind'] in {'table','records','timeline','documents','metrics','chart'} for b in p['blocks'])
    form=bool(types & {'text','number','password','textarea','datetime','choice','checkbox','file','email','tel','date','otp','rating'})
    states=['Default','Loading','Error','Offline','Stale','Restricted','Session expired']
    if read: states.append('Empty')
    if form or any(word in p['layout'] for word in ['dialog','review','offer','completion','cash']):
        states += ['Busy','Validation','Conflict','Unknown outcome','Confirmed']
    if p['id'] in {'S03','S04','S06','S15','S18','A01','A02','A03','O00','O01','O02','O03','O70'}: states.append('Rate limited')
    if 'map' in p['layout'] or p['id'] in {'S10','D10'}: states += ['Location denied','Map unavailable','Outside service area']
    if p['layout']=='offer': states.append('Expired offer')
    if p['layout'] in {'cash','receipt','finance'} or 'payment' in p['title'].lower(): states.append('Payment pending')
    if p['deferred'] or p['id'] in {'R04','R19','R20','A06','D04','O36'}: states.append('Capability unavailable')
    # The selected page's actual blocks/fields accompany these recovery profiles.
    # Empty is absent from non-collection surfaces; write-only profiles are absent
    # from read-only views. Page-specific acceptance overrides broad profiles.
    return [{"name":name,"presentation":rules[name][0],"guardrail":rules[name][1]} for name in states]


def markdown_for(p):
    lines=[f'# {p["id"]} — {p["name"]}',"","**Individually authored planning composition; not application implementation.**", "",
           f'Open [this view in the atlas](../page-atlas.html#{p["id"]}). [Page book](../'+("web-pages.md" if p["id"][0] in "AO" else "mobile-pages.md")+").", "",
           "## Purpose and capability", "", p["intro"], "", p["guardrails"], "",
           f'**Source anchor:** `{p["source"]}`. Current source is authoritative for actual data/actions.', "",
           f'**Surface:** {p["group"]}. **Composition:** {p["layout"]}. **Proposed visible title:** “{p["title"]}”.', "",
           'Entry/return paths and linked commands are in [navigation.md](../navigation.md). The [wave ledger](../wave-assignment.md) assigns this view to a delivery wave; approval of design is separate from native acceptance.', "",
           "## Ordered visual anatomy", "", p["composition"], ""]
    for idx,b in enumerate(p["blocks"],1):
        lines += [f'### {idx}. {b["title"]}', "", f'Treatment: **{b["kind"]}**.']
        for item in b["items"]:
            lines += ["",f'- **{item["label"]}**: {item["value"] or "Empty draft / no presumed server value"}. Control: {item["type"]}.']
            if item.get("options"): lines += [f'  Choices: {", ".join(item["options"])}.']
            if item.get("help"): lines += [f'  {item["help"]}']
    lines += ["", "## Actions and navigation", "",p["controls"], ""]
    for a in p["actions"]: lines += [f'- **{a["label"]}** — {a["role"]}; {a["effect"]}.']
    lines += ["", "## Complete style treatment", "",
              "Owner-selected system: Folded Streets, Street Press, Glazed Machine and Notepad. The independent five-color theme menu is withdrawn. Apply the selected style through the common component contracts; do not turn abstract effects into additional user styles. See [the four-style contract](../style-options.md). All styles preserve this view’s authoritative facts, intents, eligibility and recovery. Notepad uses grayscale ruled utility, retains icons and main workflow structure, and disables decorative animation. This is a browser/specification treatment, not native acceptance.", "",
              "Use the selected style and documented typography globally. No independent palette selector or screen-local identity. The style contract owns shape/radius overrides; the dimensions below are shared interaction baselines. Page title is 24/32, body and inputs 16/24, supporting text 14/20; Arabic uses the taller defined metrics and no Latin tracking. Labels remain above fields. Primary actions are 56 dp (64 for critical driver actions), radius 12, fixed hit regions; icon targets 48 dp. Sections have 24 dp separation, cards radius 16, task sheets radius 24 at the top. Focus is the defined 2 dp contrasting ring. Selection uses wash plus explicit check/label. Destructive actions use semantic danger and a separate review. Busy preserves action geometry; disabled state has a nearby reason. Hover and press never move an essential target.", "",
              "Source data is synthetic in the atlas. Map surfaces are schematic and carry no live supply. List/table density follows the component contract. The individual anatomy above determines which elements exist; no universal dashboard template is substituted. Reduced motion removes decorative transitions; content remains available immediately. Component options and precise tokens are in [components](../components.md) and [visual system](../visual-system.md).", "",
              "## Style context", "", f"Expressive styles: {p['styleProfile']['expressiveContext']}. Notepad: {p['styleProfile']['notepad']}. Main illustration: not included. The style switch preserves all anatomy, data and intents above.", "",
              "## Responsive and Arabic rules", "",
              "At 320/360/430 dp use one task column and a reachable footer above safe area/keyboard. Increase content height rather than shrinking type at 1.3×/1.6×/2×. Desktop operations uses persistent labelled scope/navigation, then record master/detail or the specific editor; below 840 px it stacks into labelled cards and full-page detail. Arabic mirrors directional chrome and start/end alignment; maps/logos/photos are not mirrored. Mixed numbers/plates/identifiers are bidi-isolated. Never clip essential title, amount, status or action. The atlas is a browser specimen; actual Compose/native evidence remains required.", "",
              "## State-by-state plan", "", "| State | Presentation | Authority / recovery |", "| --- | --- | --- |"]
    lines.extend(f'| {s["name"]} | {s["presentation"]} | {s["guardrail"]} |' for s in p["states"])
    lines += ["", "## Page-specific acceptance", "",p["guardrails"], "", p["specific"], "",
              "Review the complete screen with long French/Arabic labels, large text, keyboard/insets, no-color status recognition and interrupted requests. Verify the actual action contract and return path. Do not mark this page accepted from the atlas or compilation. Follow [delivery.md](../delivery.md) for candidate/device/source evidence and owner confirmation.", ""]
    if p.get('expression'):
        e=p['expression']
        lines += ['## Historical artwork candidate — not selected', '',
                  f"Graphic: **{e['asset'] or 'Intentional plain surface'}**. Motion: **{e['motion'] or 'Static / normal control feedback'}**.", '',
                  f"Placement: {e['slot']}. Space budget: {e['size']}.", '', e['condition'], '',
                  'This former artwork placement is retained as history only. Main illustrations are not part of the selected four-style system. Use [style-options.md](../style-options.md) and the current four-style atlas; the [earlier atelier](../expressive-board.html) is not the implementation reference.', '']
    return "\n".join(lines)


if __name__=="__main__": main()
