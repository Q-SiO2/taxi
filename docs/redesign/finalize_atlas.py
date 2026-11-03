"""Idempotent documentation polish and complete delivery assignment."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parent
p=R/'atlas-template.html';s=p.read_text(encoding='utf8')
s=s.replace('color:#a9272a}.state-disabled','color:var(--danger,#a9272a)}.state-disabled').replace('.validation-error{color:#a9272a;','.validation-error{color:var(--danger,#a9272a);')
s=s.replace("`;--edge:${$('palette')", "`;--danger:${$('mode').value==='dark'?'#F3B5AF':'#A9272A'};--maproute:${$('palette').value==='graphite'?'#202527':PAL[$('palette').value].action};--edge:${$('palette')")
# A dark UI may sit beside a light map; map geometry needs its own opaque token.
s=s.replace('stroke="var(--action)"','stroke="var(--maproute,var(--action))"').replace('fill="var(--action)"','fill="var(--maproute,var(--action))"')
s=s.replace("function block(b,p,index){return", "function block(b,p,index){const stateName=p.states.some(x=>x.name===$('state').value)?$('state').value:'Default';const collection=['table','records','timeline','documents','metrics','chart'].includes(b.kind);if(stateName==='Empty'&&collection)return `<section class=\"block notice\" data-block=\"${index}\"><h4>${esc(b.title)}</h4><p>No ${esc(b.title.toLowerCase())} records returned for the current permitted query.</p><p class=\"help\">A failed, suppressed or restricted query uses a different explanation.</p></section>`;if(stateName==='Loading'&&collection)return `<section class=\"block\" data-block=\"${index}\"><h4>${esc(b.title)}</h4><div class=\"skeletonline\"></div><div class=\"skeletonline short\"></div><p class=\"help\">Loading ${esc(b.title.toLowerCase())}; no zero or empty result is presumed.</p></section>`;return") if 'const stateName=p.states.some' not in s else s
s=s.replace("b.kind==='map'?map(p):''", "b.kind==='map'?(stateName==='Map unavailable'?'<div class=\"mapcanvas\"><div class=\"maplegend\">Map tiles unavailable · textual journey facts retained</div></div>':map(p)):''")
s=s.replace("s=$('state').value;const closed", "s=p.states.some(x=>x.name===$('state').value)?$('state').value:'Default';const closed")
s=s.replace("${state(p)}${closed?", "${state(p)}${s==='Validation'?'<div class=\"state-notice state-error\"><strong>Review the highlighted draft constraint</strong><p>Field-local errors use the exact documented validation; focus moves to the first invalid input.</p></div>':''}${closed?")
s=s.replace("${help}</div>`}if(['choice'", "${help}${$('state').value==='Validation'&&n==='0-0'?'<p class=\"validation-error\">Example constraint error · verify the field requirement above.</p>':''}</div>`}if(['choice'")
p.write_text(s,encoding='utf8')
data=json.loads((R/'atlas-data.json').read_text(encoding='utf8'))
def wave(p):
 key=p['id'];n=int(key[1:]);prefix=key[0]
 if prefix=='L':return 'Deferred B/C capability design'
 if key=='R04':return 'B provider-search acceptance'
 if prefix=='S':return 'UX-5' if n>=14 or n==12 else 'UX-2'
 if prefix=='R':return 'UX-8' if n in {19,20,24,25,26,27,28,29} else 'UX-5' if n in {30,31,32,33,34,35,39,40} else 'UX-2' if n<=10 or n in {38,41,42} else 'UX-3'
 if prefix=='D':return 'UX-8' if n in {14,26,27,34} else 'UX-4' if 10<=n<=25 or n in {38,41} else 'UX-5'
 if prefix=='A':return 'UX-5'
 return 'UX-6' if n<=16 or n in {31,34,35,36,37,40,41,47,48,60,61,62,63,64,65,66,67,70,71,75,84,85,86,87} else 'UX-8'
assigned=[dict(id=p['id'],name=p['name'],wave=wave(p),spec=p['spec']) for p in data]
(R/'wave-assignment.json').write_text(json.dumps(assigned,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
lines=['# Every-view delivery assignment','','**Proposed; starts only after owner confirmation.** Full design coverage and implementation order are separate. All 213 compositions are reviewable now; UX-1 establishes a shared foundation for every delivered surface. UX-2–UX-6 execute core and participant/representative console flows; UX-8 completes secondary editor/workflow polish. UX-7 validates all alpha-reachable pages and explicitly discloses remaining secondary acceptance. Deferred rows do not authorize unsupported backend work.','','A view inherited by multiple roles is assigned once and reused; no duplicate app implementation. R42 is development-only and excluded from the presentation/release navigation. Scope-specific/capability-gated views remain unavailable until their real contracts are accepted.','','[Delivery details](delivery.md). [Every visual composition](page-atlas.html).','','| View | Wave | Full specification |','| --- | --- | --- |']
lines += [f"| [{a['id']} {a['name']}](page-atlas.html#{a['id']}) | {a['wave']} | [Spec]({a['spec']}) |" for a in assigned]
(R/'wave-assignment.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('Completed state preview polish and assigned every view to a delivery wave.')
