"""Check authored coverage, build consistency and review-only boundaries."""
from pathlib import Path
import json,re,hashlib,subprocess,tempfile
R=Path(__file__).resolve().parent
repo=R.parent.parent
pages=json.loads((R/'atlas-data.json').read_text(encoding='utf8'))
manifest=json.loads((R/'atlas-manifest.json').read_text(encoding='utf8'))
ids={p['id'] for p in pages}
assert len(ids)==len(pages)==manifest['pages']==213
assert manifest['uniqueCompositions']==213
assert len(list((R/'pages').glob('*.md')))==213
assert len({json.dumps(p['blocks'],sort_keys=True) for p in pages})==213
for p in pages:
 assert p['actions'] and p['blocks'] and p['states'] and p['specific'] and p['guardrails'],p['id']
 assert p['states'][0]['name']=='Default',p['id']
 assert all(b['items'] and b['title'] and b['kind'] for b in p['blocks']),p['id']
 spec=(R/p['spec']).read_bytes()
 assert hashlib.sha256(spec).hexdigest()==p['specSha256'],p['id']
 if p['id'][0]!='L':assert (repo/p['source']).is_file(),p['id']
 for b in p['blocks']:
  for i in b['items']:assert i['label'] and i['type'],p['id']
for item in manifest['sourceInputs']:assert hashlib.sha256((R/item['file']).read_bytes()).hexdigest()==item['sha256']
inventory=json.loads((R/'source-ui-inventory.json').read_text(encoding='utf8'))
for row in inventory:
 assert (repo/row['source']).is_file()
 for v in row['designRefs']:assert v in ids or re.fullmatch(r'C(0[1-9]|[123][0-9]|40)',v),row
sourceFiles=json.loads((R/'source-ui-files.json').read_text(encoding='utf8'))
assert len(sourceFiles)==manifest['sourceAudit']['files'] and len(inventory)==manifest['sourceAudit']['declarations']
sourceRoots=['TaxiMobile/shared/src/commonMain','TaxiMobile/shared/src/androidMain','TaxiMobile/shared/src/iosMain','TaxiMobile/webApp/src/webMain']
actualSources={p.relative_to(repo).as_posix() for area in sourceRoots for p in (repo/area).rglob('*.kt') if '@Composable' in p.read_text(encoding='utf8')}
listedSources=[f['source'] for f in sourceFiles]
assert len(listedSources)==len(set(listedSources)), 'Duplicate source files in inventory'
assert set(listedSources)==actualSources, {'missing':sorted(actualSources-set(listedSources)), 'removed':sorted(set(listedSources)-actualSources)}
for f in sourceFiles:assert hashlib.sha256((repo/f['source']).read_bytes()).hexdigest()==f['sha256']
waves=json.loads((R/'wave-assignment.json').read_text(encoding='utf8'))
assert {w['id'] for w in waves}==ids and len(waves)==len(ids)
for name in ['page-atlas.html','component-gallery.html','direction-board.html']:
 content=(R/name).read_text(encoding='utf8')
 assert not any(v in content for v in ['fetch(','XMLHttpRequest','WebSocket(','axios.','__PAGE_DATA__']),name
 for script in re.findall(r'<script>(.*?)</script>',content,re.S):
  with tempfile.NamedTemporaryFile(suffix='.js',delete=False) as temp:
   target=Path(temp.name);target.write_text(script,encoding='utf8')
  result=subprocess.run(['node','--check',str(target)],capture_output=True,text=True)
  target.unlink()
  assert result.returncode==0,name+' '+result.stderr
 for rel in re.findall(r'(?:href|src)=[\'\"]([^\'\"]+)',content):
  if re.match(r'^(?:https?:|#)',rel) or '${' in rel:continue
  assert (R/rel.split('#')[0]).exists(),(name,rel)
component=(R/'component-gallery.html').read_text(encoding='utf8')
assert len(re.findall(r'<article id="C\d\d">',component))==40
result={'pages':len(pages),'uniqueCompositions':manifest['uniqueCompositions'],'componentSpecimens':40,'sourceDeclarations':len(inventory),'sourceFiles':len(sourceFiles),'contentControlItems':sum(len(b['items']) for p in pages for b in p['blocks']),'authoredSections':sum(len(p['blocks']) for p in pages),'allViewsAssignedToWaves':True,'scriptSyntax':'PASS','reviewOnlyNoApi':'PASS','sourceHashes':'PASS','specHashes':'PASS'}
(R/'artifact-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
