"""Check abstract review artifacts; does not accept a brand or native app."""
from pathlib import Path
import json
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parent
html = (root / 'abstract-lab.html').read_text(encoding='utf8')
assert not any(s in html for s in ['fetch(', 'XMLHttpRequest', 'WebSocket(', 'axios.'])
for link in re.findall(r'(?:href|src)=[\'\"]([^\'\"]+)', html):
    if link.startswith(('#', 'http')) or '${' in link:
        continue
    assert (root / link.split('#')[0]).exists(), link
for script in re.findall(r'<script>(.*?)</script>', html, re.S):
    with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as target:
        path = Path(target.name)
    try:
        path.write_text(script, encoding='utf8')
        result = subprocess.run(['node', '--check', str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    finally:
        path.unlink()
for effect in ['fold', 'print', 'tactile', 'notepad']:
    assert f'data-style="{effect}"' in html
assert 'identity-assets/${world}.png' not in html
assert 'prefers-reduced-motion' in html and 'visibilitychange' in html
assert 'IntersectionObserver' in html
result = {
    'date': '2026-10-15', 'selectedStyles': 4, 'expressivePerformances': 3,
    'primaryMainIllustration': False,
    'originalProceduralGraphics': True,
    'scriptSyntax': 'PASS', 'localLinks': 'PASS', 'reviewOnlyNoApi': 'PASS',
    'directionSelectedByOwner': True, 'nativeImplementationVerified': False,
}
(root / 'abstract-check.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps(result))
