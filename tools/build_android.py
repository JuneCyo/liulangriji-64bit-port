"""Build the offline Java/WebView APK using the workspace-local Android tools."""
import datetime
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
BUILD_TOOLS = ROOT / '.tools/sdk-packages/build-tools-35.0.0/android-15'
ANDROID_JAR = ROOT / '.tools/sdk-packages/platforms-android-35/android-35/android.jar'
BUILD = ROOT / 'artifacts/build' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
SIGNING = ROOT / '.tools/signing'
DEBUG = '--debug' in sys.argv


def run(args, label):
    print(label, flush=True)
    result = subprocess.run([str(x) for x in args], cwd=ROOT, capture_output=True)
    for data in (result.stdout, result.stderr):
        try: text = data.decode('utf-8')
        except UnicodeDecodeError: text = data.decode('gb18030', errors='replace')
        if text.strip(): print(text.strip(), flush=True)
    if result.returncode: raise RuntimeError(f'{label} failed ({result.returncode})')


def main():
    if not (ROOT / 'web/cocos2d-js-min.js').is_file():
        raise FileNotFoundError('Build the Web engine first')
    for folder in ('generated', 'classes', 'dex'):
        (BUILD / folder).mkdir(parents=True, exist_ok=True)
    icon = ROOT / 'android/res/drawable/icon.png'
    icon.parent.mkdir(parents=True, exist_ok=True)
    if not icon.exists():
        original_icon = ROOT / 'analysis/apk/res/mipmap-xxhdpi-v4/ic_launcher.png'
        if not original_icon.exists(): raise FileNotFoundError('Missing android/res/drawable/icon.png')
        shutil.copyfile(original_icon, icon)
    resources = BUILD / 'compiled-res.zip'
    unsigned = BUILD / 'unsigned.apk'
    aligned = BUILD / 'aligned.apk'
    signed = BUILD / 'signed.apk'
    run([BUILD_TOOLS / 'aapt2.exe', 'compile', '--dir', ROOT / 'android/res', '-o', resources], 'Compile Android resources')
    link = [BUILD_TOOLS / 'aapt2.exe', 'link', '-I', ANDROID_JAR, '--manifest', ROOT / 'android/AndroidManifest.xml',
            '-o', unsigned, '--java', BUILD / 'generated', '-A', ROOT / 'web', resources]
    if DEBUG: link.append('--debug-mode')
    run(link, 'Package original game assets')
    sources = list((ROOT / 'android/src').rglob('*.java')) + list((BUILD / 'generated').rglob('*.java'))
    run(['javac', '-encoding', 'UTF-8', '--release', '8', '-classpath', ANDROID_JAR,
         '-d', BUILD / 'classes', *sources], 'Compile Android host')
    classes = list((BUILD / 'classes').rglob('*.class'))
    run(['java', '-cp', BUILD_TOOLS / 'lib/d8.jar', 'com.android.tools.r8.D8',
         '--lib', ANDROID_JAR, '--min-api', '23', '--output', BUILD / 'dex', *classes], 'Build Android DEX')
    repacked = BUILD / 'repacked.apk'
    with zipfile.ZipFile(unsigned) as original, zipfile.ZipFile(repacked, 'w') as z:
        for entry in original.infolist():
            z.writestr(entry.filename, original.read(entry), compress_type=entry.compress_type)
        for dex in (BUILD / 'dex').glob('*.dex'):
            z.write(dex, dex.name, compress_type=zipfile.ZIP_DEFLATED)
    run([BUILD_TOOLS / 'zipalign.exe', '-f', '4', repacked, aligned], 'Align APK')
    SIGNING.mkdir(parents=True, exist_ok=True)
    keystore, password = SIGNING / 'local-port.p12', SIGNING / 'keystore-password.txt'
    if not keystore.exists():
        if not password.exists(): password.write_text(secrets.token_urlsafe(32), encoding='ascii')
        run(['keytool', '-genkeypair', '-keystore', keystore, '-storetype', 'PKCS12',
             '-storepass:file', password, '-alias', 'local-port', '-keyalg', 'RSA', '-keysize', '3072',
             '-validity', '10000', '-dname', 'CN=Stray Diary Local Port'], 'Create local signing key')
    run(['java', '-jar', BUILD_TOOLS / 'lib/apksigner.jar', 'sign', '--ks', keystore,
         '--ks-key-alias', 'local-port', '--ks-pass', 'file:' + str(password), '--out', signed, aligned], 'Sign APK')
    run(['java', '-jar', BUILD_TOOLS / 'lib/apksigner.jar', 'verify', '--verbose', signed], 'Verify APK signature')
    run([BUILD_TOOLS / 'zipalign.exe', '-c', '4', signed], 'Verify APK alignment')
    with zipfile.ZipFile(signed) as z:
        if z.testzip() is not None: raise ValueError('APK CRC failed')
        if any(x.startswith('lib/') for x in z.namelist()): raise ValueError('Unexpected native libraries')
        originals = json.loads((ROOT / 'docs/original-assets.json').read_text(encoding='utf8'))
        for entry in originals:
            actual = hashlib.sha256(z.read('assets/' + entry['path'])).hexdigest()
            if actual != entry['sha256']: raise ValueError('Original asset changed: ' + entry['path'])
    dist = ROOT / ('artifacts/debug' if DEBUG else 'dist')
    dist.mkdir(parents=True, exist_ok=True)
    target = dist / ('流浪日记-测试版.apk' if DEBUG else '流浪日记-安卓兼容版.apk')
    shutil.copyfile(signed, target)
    manifest = ET.parse(ROOT / 'android/AndroidManifest.xml').getroot()
    ns = '{http://schemas.android.com/apk/res/android}'
    metadata = {'file': target.name, 'package': manifest.attrib['package'],
                'version': manifest.attrib[ns + 'versionName'], 'version_code': int(manifest.attrib[ns + 'versionCode']),
                'min_android_api': 23, 'target_android_api': 35, 'native_libraries': [],
                'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'checks': ['APK ZIP CRC', 'APK v1/v2/v3 signature', 'ZIP alignment', 'all original assets unchanged'],
                'build_directory': str(BUILD), 'debug': DEBUG}
    (dist / 'android-build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
