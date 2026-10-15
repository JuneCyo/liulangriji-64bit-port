"""Restore the game's original scripts and resources into a local Web build."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / 'artifacts/original/StrayDiary-original.apk'
WEB = ROOT / 'web'
(ROOT / 'docs').mkdir(exist_ok=True)

with zipfile.ZipFile(APK) as z:
    copied = []
    for name in z.namelist():
        if name.startswith('assets/res/') or name in ('assets/main.js', 'assets/src/project.js', 'assets/src/settings.js', 'assets/project.json'):
            if name.endswith('/'):
                continue
            relative = name.removeprefix('assets/')
            target = WEB / relative
            if not target.resolve().is_relative_to(WEB.resolve()):
                raise ValueError('Unsafe asset path')
            target.parent.mkdir(parents=True, exist_ok=True)
            data = z.read(name)
            target.write_bytes(data)
            copied.append({'path': relative, 'sha256': hashlib.sha256(data).hexdigest()})
    (ROOT / 'docs/original-assets.json').write_text(json.dumps(copied, indent=2), encoding='utf-8')
    print(f'Restored {len(copied)} original files without changing their contents')
