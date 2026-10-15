"""Package a Windows tray launcher; no Python/Node installation needed to play."""
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf8')
DIST = ROOT / 'dist/电脑版'
CSC = Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
DIST.mkdir(parents=True, exist_ok=True)
if not CSC.exists(): raise FileNotFoundError('Windows .NET Framework C# compiler not available')
shutil.copytree(ROOT / 'web', DIST / 'web', dirs_exist_ok=True)
exe = DIST / '流浪日记电脑版.exe'
args = [str(CSC), '/nologo', '/target:winexe', '/platform:anycpu', '/optimize+',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/out:' + str(exe), str(ROOT / 'pc/Launcher.cs')]
result = subprocess.run(args, capture_output=True)
if result.returncode:
    print(result.stdout.decode('gb18030', errors='replace'))
    print(result.stderr.decode('gb18030', errors='replace'))
    raise RuntimeError('PC launcher compilation failed')
readme = '''流浪日记电脑版\n\n完整解压后，双击“流浪日记电脑版.exe”。游戏将在默认浏览器中打开。\n不需要安卓模拟器，也不需要安装 Python 或 Node.js。\n\n程序在本机 127.0.0.1:18766 提供游戏文件，不连接外部服务器。\n托盘图标右键菜单可重新打开游戏或退出后台程序。\n关闭浏览器标签页后，托盘程序仍保留；游玩结束可右键托盘图标退出。\n\n使用同一个浏览器和普通浏览模式游玩。存档保存在浏览器本地；清理站点数据、使用隐私模式或切换浏览器会影响存档。\n可通过顶部“存档”菜单导出 JSON 文件，并在手机兼容版中导入；反向操作同样支持。\n\n请保留整个 web 文件夹。请勿在游玩过程中退出托盘程序，否则后续场景资源可能无法加载。\n这是基于用户提供的原版安装包制作的个人兼容版本。原游戏剧情、代码及美术归原作者；引擎版权与许可见 web/NOTICE.txt。\n'''
(DIST / '使用说明.txt').write_text(readme, encoding='utf-8-sig')
archive = ROOT / 'dist/流浪日记-电脑版.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for file in DIST.rglob('*'):
        if file.is_file(): z.write(file, str(file.relative_to(DIST.parent)))
metadata = {'file': archive.name, 'bytes': archive.stat().st_size,
            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'launcher': str(exe),
            'port': 18766, 'requirements': ['Windows .NET Framework 4.x', 'modern browser']}
(ROOT / 'dist/pc-build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(metadata, ensure_ascii=True, indent=2))
