"""Consistency checks for the documentation-only expressive package."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent
data=json.loads((R/'expressive-data.json').read_text(encoding='utf8'))
manifest=json.loads((R/'expressive-manifest.json').read_text(encoding='utf8'))
base=json.loads((R/'atlas-data.json').read_text(encoding='utf8'))
art={a['id'] for a in data['art']};motion={m['id'] for m in data['motion']}
assert len(art)==len(data['art'])==24 and len(motion)==len(data['motion'])==18
assert {p['id'] for p in data['pages']}=={p['id'] for p in base} and len(data['pages'])==213
for p in data['pages']:
 assert p['asset'] is None or p['asset'] in art
 assert p['motion'] is None or p['motion'] in motion
 assert p['slot'] and p['size'] and p['condition']
for m in data['motion']:
 assert m['asset'] in art and m['native'] and m['trigger'] and m['effect']
 assert 100<=m['duration']<=2400 and 1<=m['iterations']<=3
for f in manifest['inputs']:assert hashlib.sha256((R/f['file']).read_bytes()).hexdigest()==f['sha256']
for a in json.loads((R/'expressive-assets.json').read_text(encoding='utf8')):
 f=R/a['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']
 tree=ET.parse(f);assert tree.getroot().get('viewBox')=='0 0 320 240'
 assert not any(e.tag.split('}')[-1] in {'script','image','foreignObject'} for e in tree.iter())
 assert not any('href' in k for e in tree.iter() for k in e.attrib)
content=(R/'expressive-board.html').read_text(encoding='utf8')
assert '__EXPRESSIVE_DATA__' not in content
assert not any(s in content for s in ['fetch(','WebSocket(','XMLHttpRequest','axios.','https://cdn.'])
for src in re.findall(r'(?:href|src)=[\'\"]([^\'\"]+)',content):
 if src.startswith(('http','#')) or '${' in src:continue
 assert (R/src.split('#')[0].split('?')[0]).exists(),src
for script in re.findall(r'<script>(.*?)</script>',content,re.S):
 with tempfile.NamedTemporaryFile(suffix='.js',delete=False) as f:target=Path(f.name)
 target.write_text(script,encoding='utf8');result=subprocess.run(['node','--check',str(target)],capture_output=True,text=True);target.unlink()
 assert result.returncode==0,result.stderr
research=(R/'expressive-research.md').read_text(encoding='utf8')
refs=re.findall(r'^\| \[.+?\]\((https://[^)]+)\)',research,re.M)
assert len(refs)==34 and len(set(refs))==34
result={'graphicMasters':24,'motionStudies':18,'pagePlacements':213,'primaryResearchReferences':34,'originalSvgXmlAndHashes':'PASS','recipeReferencesAndBounds':'PASS','pageCoverage':'PASS','scriptSyntax':'PASS','localLinks':'PASS','reviewOnlyNoApi':'PASS'}
(R/'expressive-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result))
