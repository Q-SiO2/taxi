"""Verify the review-only identity lab without treating design checks as approval."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'identity-manifest.json').read_text(encoding='utf8'))
assert manifest['status'] == 'EXPLORATION_UNAPPROVED'
assert manifest['previousCityScene'] == 'REJECTED'
assert manifest['themesAreIdentity'] is False
assert len(manifest['assets']) == 4
for item in manifest['assets']:
    data = (root / item['file']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == item['sha256']
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    if 'taxi-layer' in item['file']:
        assert data[25] == 6, 'Vehicle PNG must include an alpha channel'

html = (root / 'identity-lab.html').read_text(encoding='utf8')
assert not any(value in html for value in ['fetch(', 'XMLHttpRequest', 'WebSocket(', 'axios.'])
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

inventory = json.loads((root / 'atlas-data.json').read_text(encoding='utf8'))
ids = {item['id'] for item in inventory}
assert len(inventory) == len(ids) == 213
for view in ['S02', 'R05', 'D13', 'R18']:
    assert view in ids and f"id:'{view}'" in html
for world in ['tactile', 'print', 'fold']:
    assert f'value="{world}"' in html
assert 'prefers-reduced-motion' in html and 'visibilitychange' in html
assert 'IntersectionObserver' in html and "dataset.phase='suppressed'" in html
result = {
    'date': '2026-10-14',
    'artWorlds': 3,
    'conceptPngs': 4,
    'comparativeInterfaceCompositions': 12,
    'structuralInventoryRetained': 213,
    'assetHashesAndVehicleAlphaChannel': 'PASS',
    'localLinks': 'PASS',
    'scriptSyntax': 'PASS',
    'reviewOnlyNoApi': 'PASS',
    'identityAccepted': False,
    'nativeImplementationVerified': False,
}
(root / 'identity-check.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps(result))
