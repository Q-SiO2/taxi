"""Verify selected four-style specimens, exact coverage and token contrast."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parent
ids = ['fold', 'print', 'tactile', 'notepad']
names = ['Folded Streets', 'Street Press', 'Glazed Machine', 'Notepad']
html = (root / 'abstract-lab.html').read_text(encoding='utf8')
assert set(re.findall(r'data-style="(.*?)"', html)) == set(ids)
select = re.search(r'<select id="world">(.*?)</select>', html).group(1)
assert re.findall(r'value="(.*?)"', select) == ids
assert all(name in select for name in names)
assert "$('play').disabled=world==='notepad'" in html
assert "$('timeline').disabled=world==='notepad'" in html
assert "world==='notepad'?0:Math.sin" in html
assert 'taximobile.designReview.style' in html
assert 'Preview storage unavailable' in html
assert 'function icon(name)' in html
assert 'prefers-reduced-motion' in html and 'visibilitychange' in html

for file in ['abstract-lab.html', 'page-atlas.html', 'component-gallery.html']:
    content = (root / file).read_text(encoding='utf8')
    assert not any(s in content for s in ['fetch(', 'XMLHttpRequest', 'WebSocket(', 'axios.'])
    for link in re.findall(r'(?:href|src)=[\'\"]([^\'\"]+)', content):
        if link.startswith(('#', 'http')) or '${' in link:
            continue
        assert (root / link.split('#')[0].split('?')[0]).exists(), link
    for script in re.findall(r'<script>(.*?)</script>', content, re.S):
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as target:
            path = Path(target.name)
        try:
            path.write_text(script, encoding='utf8')
            result = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
        finally:
            path.unlink()

atlas = (root / 'atlas-template.html').read_text(encoding='utf8')
assert 'id="palette"' not in atlas
for legacy in ['forest', 'orchid', 'electric', 'terracotta', 'graphite']:
    assert f'value="{legacy}"' not in atlas
palette_source = re.search(r'const PAL=(.*?);\nconst TYPES=', atlas, re.S).group(1)
tokens = json.loads(subprocess.check_output(['node', '-e', 'process.stdout.write(JSON.stringify(' + palette_source + '))'], text=True))
assert set(tokens) == set(ids)
def lum(color):
    values = [int(color[n:n+2], 16) / 255 for n in [1, 3, 5]]
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(values, [.2126, .7152, .0722]))
def contrast(a, b):
    high, low = sorted([lum(a), lum(b)], reverse=True)
    return (high + .05) / (low + .05)
pairs = []
for style, token in tokens.items():
    for name, a, b, minimum in [('body', 'ink', 'surface', 4.5), ('supporting', 'secondary', 'surface', 4.5), ('action', 'label', 'action', 4.5), ('control', 'stroke', 'surface', 3)]:
        ratio = contrast(token[a], token[b])
        assert ratio >= minimum, (style, name, ratio)
        pairs.append({'style': style, 'pair': name, 'ratio': round(ratio, 2), 'minimum': minimum})
for color in tokens['notepad'].values():
    assert color[1:3].upper() == color[3:5].upper() == color[5:7].upper()

pages = json.loads((root / 'atlas-data.json').read_text(encoding='utf8'))
ledger = json.loads((root / 'style-coverage.json').read_text(encoding='utf8'))
assert len(pages) == len(ledger) == 213
assert {p['id'] for p in pages} == {p['id'] for p in ledger}
stable = {'folded_streets', 'street_press', 'glazed_machine', 'notepad'}
for page in pages:
    assert set(page['styleProfile']['styles']) == stable
    assert not page['styleProfile']['mainIllustration']
    spec = (root / page['spec']).read_bytes()
    assert hashlib.sha256(spec).hexdigest() == page['specSha256']
    assert b'../style-options.md' in spec and b'Notepad' in spec
    assert 'no decorative animation' in page['styleProfile']['notepad']
settings = next(p for p in pages if p['id'] == 'S12')
choices = [i for b in settings['blocks'] for i in b['items'] if i['label'] == 'Visual style']
assert choices[0]['options'] == names
component = (root / 'component-gallery.html').read_text(encoding='utf8')
assert all(f'value="{style}"' in component for style in ids)

result = {'date': '2026-10-15', 'selectedStyles': names, 'styles': 4,
          'pagesWithAllStyles': 213, 'componentSpecimens': 40,
          'notepadTokensGrayscale': 'PASS', 'notepadDecorativeMotionDisabled': 'PASS',
          'preferenceSelectionContract': 'PASS', 'sourceAndSpecCoverage': 'PASS',
          'scriptSyntax': 'PASS', 'localLinks': 'PASS', 'reviewOnlyNoApi': 'PASS',
          'contrastPairs': pairs, 'directionSelectedByOwner': True,
          'nativeImplementationVerified': False}
(root / 'styles-check.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k != 'contrastPairs'}))
