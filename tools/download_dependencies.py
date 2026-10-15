"""Download official build inputs into this workspace and check SDK hashes."""
import concurrent.futures
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.tools/downloads'


def download(url, target, checksum=None, algorithm='sha1'):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (not checksum or hashlib.new(algorithm, target.read_bytes()).hexdigest() == checksum):
        print(f'Cached: {target.name}', flush=True)
        return target
    print(f'Downloading: {target.name}', flush=True)
    partial = target.with_suffix(target.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=60) as response, partial.open('wb') as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    if checksum and hashlib.new(algorithm, partial.read_bytes()).hexdigest() != checksum:
        raise ValueError(f'Checksum mismatch: {target}')
    partial.replace(target)
    print(f'Downloaded: {target.name} ({target.stat().st_size} bytes)', flush=True)
    return target


def unzip(archive, target):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            out = target / item.filename
            if not out.resolve().is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path')
        z.extractall(target)


def sdk():
    metadata = download('https://dl.google.com/android/repository/repository2-3.xml', CACHE / 'repository2-3.xml')
    tree = ET.parse(metadata)
    records = []
    for desired in ('build-tools;35.0.0', 'platforms;android-35', 'platform-tools'):
        package = next(x for x in tree.getroot() if x.tag.endswith('remotePackage') and x.get('path') == desired)
        archives = package.find('archives').findall('archive')
        archive = next(x for x in archives if x.findtext('host-os') in (None, 'windows'))
        complete = archive.find('complete')
        relative = complete.findtext('url')
        digest = complete.find('checksum')
        dest = CACHE / Path(relative).name
        download('https://dl.google.com/android/repository/' + relative, dest, digest.text, digest.get('type', 'sha1'))
        unpack = ROOT / '.tools/sdk-packages' / desired.replace(';', '-')
        unzip(dest, unpack)
        records.append({'package': desired, 'archive': relative, 'checksum': digest.text,
                        'algorithm': digest.get('type', 'sha1'), 'directory': str(unpack)})
    (ROOT / '.tools/sdk-packages.json').write_text(json.dumps(records, indent=2), encoding='utf-8')


def engine():
    revision = 'ada2855dbeb5c2913a4f44d2947854daea9aa3f5'
    archive = download(f'https://codeload.github.com/cocos/cocos-engine/zip/{revision}', CACHE / f'cocos-engine-{revision}.zip')
    unzip(archive, ROOT / '.tools/cocos')
    (ROOT / '.tools/engine-source.json').write_text(json.dumps({'repository': 'https://github.com/cocos/cocos-engine',
        'tag': '1.9', 'revision': revision, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(sdk), pool.submit(engine)]
        for future in futures:
            future.result()
