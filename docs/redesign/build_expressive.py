"""Build the expressive concept board and every-page placement ledger."""
from pathlib import Path
import json,runpy,hashlib
R=Path(__file__).resolve().parent
assets=runpy.run_path(str(R/'expressive_assets.py'))
assets['main']()
catalog=runpy.run_path(str(R/'expressive_catalog.py'))
pages=json.loads((R/'atlas-data.json').read_text(encoding='utf8'))
placements=[dict(id=p['id'],name=p['name'],group=p['group'],layout=p['layout'],**catalog['placement'](p)) for p in pages]
payload={'art':[{k:v for k,v in a.items() if k!='content'}|{'svg':assets['svg'](a)} for a in assets['ART'].values()],'motion':catalog['MOTIONS'],'pages':placements}
assert len(placements)==213 and len({p['id'] for p in placements})==213
assert all(p['asset'] is None or p['asset'] in assets['ART'] for p in placements)
assert all(p['motion'] is None or p['motion'] in {m['id'] for m in catalog['MOTIONS']} for p in placements)
(R/'expressive-data.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
template=(R/'expressive-template.html').read_text(encoding='utf8')
data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
(R/'expressive-board.html').write_text(template.replace('__EXPRESSIVE_DATA__',data),encoding='utf8')
lines=['# Decoration and motion assignment for every view','','**Proposed 14 October 2026; owner approval pending.** Every existing design ID has a placement decision. A blank-art decision is intentional, not an omitted page. Exact illustration/motion recipes are in [expressive-motion.md](expressive-motion.md), editable masters in [the art manifest](expressive-assets.json), and all variants in the [visual motion board](expressive-board.html).','','Decorative geometry is not a replacement for a real map, record, payment, driver identity, credential or route. Entry motion leaves text and controls immediately available. Reduce-motion, hidden/offscreen and active-driver contexts have static fallbacks.','','| View | Graphic | Motion | Placement / size | Specific condition |','| --- | --- | --- | --- | --- |']
for p in placements:
 lines.append(f"| [{p['id']} {p['name']}](page-atlas.html#{p['id']}) | {p['asset'] or 'Intentional plain view'} | {p['motion'] or 'Static / normal control feedback'} | {p['slot']}; {p['size']} | {p['condition']} |")
(R/'expressive-pages.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
lines=['# Motion recipe catalogue','','**Proposed; browser studies are not native acceptance.** All 18 studies have individual Play/Stop/Scrub controls and a static end pose. Reduced motion skips movement; active-driver and dense-review contexts suppress decorative playback. Native implementation uses existing Compose APIs first.','','| ID / study | Asset | Timing | Effect / actual trigger | Compose recreation |','| --- | --- | --- | --- | --- |']
for m in catalog['MOTIONS']:
 lines.append(f"| {m['id']} {m['name']} | {m['asset']} | {m['duration']} ms × at most {m['iterations']}; {m['easing']} | {m['effect']} Trigger: {m['trigger']} | {m['native']} |")
(R/'expressive-recipes.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
manifest=dict(graphics=len(payload['art']),motions=len(payload['motion']),pages=len(placements),plainViews=sum(p['asset'] is None for p in placements),motionAssignedViews=sum(p['motion'] is not None for p in placements),artDirections=['Paper cut','Line chronicle','Print studio'],inputs=[{'file':f,'sha256':hashlib.sha256((R/f).read_bytes()).hexdigest()} for f in ['expressive_assets.py','expressive_catalog.py','expressive-template.html','atlas-data.json']])
(R/'expressive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(json.dumps(manifest))
