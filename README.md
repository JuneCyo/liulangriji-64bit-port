# 流浪日记 64 位安卓兼容版 / Windows 电脑版

基于《流浪日记》原版 APK 1.21 的脚本、场景和图片恢复运行环境，提供可在 64 位安卓系统上运行的 APK，以及 Windows 本地浏览器启动器。这是非官方兼容工程，原游戏版权归晓风游戏及原作者。

安卓端通过系统 WebView 执行游戏，**不包含重新编译的 ARM64 Cocos 原生引擎**。仓库包含打包后的原版 JavaScript 和资源，以及本工程的宿主、启动器和构建代码；不是原作者的完整 Creator 编辑器工程。

## 下载与使用

在 [Releases](https://github.com/JuneCyo/liulangriji-64bit-port/releases/latest) 下载：

| 文件 | 用途 |
| --- | --- |
| `StrayDiary-Android-1.21-port.3.apk` | 手机安装包，Android 6.0 或以上，需要系统 WebView |
| `StrayDiary-Windows.zip` | 完整电脑版，解压后运行其中的 EXE；推荐下载这个文件 |
| `StrayDiary-Windows-Launcher.exe` | 单独的电脑启动器；必须和完整包中的 `web` 文件夹放在一起，不能单独运行游戏 |
| `SHA256SUMS.txt` | Release 附件的 SHA-256 校验值 |

手机端桌面名称为“流浪日记兼容版”，包名 `local.straydiary.port`，与原版独立安装。已有本工程旧兼容版时直接覆盖安装可保留存档；卸载会删除应用本地数据。

电脑版需要 Windows .NET Framework 4.x 和现代浏览器，不需要安卓模拟器、Python 或 Node.js。启动器在 `127.0.0.1:18766` 提供本地游戏文件；托盘图标右键菜单可重新打开游戏或退出。游玩期间请保持启动器运行。

两端均支持顶部“存档 → 导出存档 / 导入存档”。通过 JSON 文件手动转移进度，不提供云同步。电脑端请使用同一个浏览器的普通模式，清理站点数据会影响存档。

## 当前版本

- 安卓 `1.21-port.3`（版本号 12103）：硬件加速、目标 60 FPS；启动时以原版开始菜单静态预览替代白色加载页和进度条，游戏首帧完成后接入可操作菜单。预览期间仍需短暂初始化，按钮尚不可操作。
- 电脑版 Release 为此前验证通过的完整包；本次发布没有改动其启动器或游戏文件。
- 原版主菜单内的 `0.921` 文案沿用原始资源，与兼容 APK 版本号不同。

## 工程结构

```text
android/               Java WebView 宿主、Manifest、应用图标
pc/Launcher.cs         Windows 托盘启动器与本地 HTTP 服务
web/                   游戏运行文件、原版脚本与资源、存档菜单、启动预览
web/licenses/          引擎与第三方许可
tools/                 Windows 构建与依赖下载脚本
docs/original-assets.json  94 个原始文件的 SHA-256 清单
```

## 从代码构建

构建环境为 Windows、Python 3.10+、JDK 17、Node.js 18+ 和 npm。运行脚本时工作目录为仓库根目录。运行游戏本身不需要这些构建工具。

```powershell
# 下载 Android SDK 工具及固定版本的官方 Cocos 引擎源码到 .tools/
python tools/download_dependencies.py

# 仓库已包含可用引擎包；需要重新编译引擎时执行以下两条
npm ci --prefix tools/js-build
node tools/build_web_engine.cjs

# 制作正式 APK，输出到 dist/
python tools/build_android.py

# 制作电脑版 EXE 和完整 ZIP，输出到 dist/
python tools/build_pc.py
```

Android SDK 使用 Build Tools 35.0.0 和 API 35。Cocos 引擎固定为官方 tag `1.9` 对应提交 `ada2855dbeb5c2913a4f44d2947854daea9aa3f5`。引擎兼容修改包含关闭自动浏览器全屏、安卓 Canvas 2D / 60 FPS 设置及启动首帧交接。

首次构建 APK 会在 `.tools/signing/` 生成本地签名密钥。该目录不会提交到仓库。自行构建的签名与 Release 不同，不能直接覆盖安装 Release APK；需要继续更新同一自建应用时，请保留自己的签名密钥。

`tools/prepare_web.py` 用于从自行准备的原始 APK 恢复原版资源。正常构建不需要再次提取；原始 APK、模拟器磁盘和个人存档不包含在仓库中。

## 验证范围

已检查 APK 签名、ZIP 对齐、正式包关闭调试及 94 个原始文件的完整性；已测试主菜单、新开局、剧情、前进、战斗、逃跑、存档导入导出、保存及继续游戏。第三版另检查了模拟器冷启动录像和首帧交接。

电脑测试环境为 Windows + Chrome，以及 Android 12 / WebView 101 模拟器（x86_64，应用运行于 `app_process64`）。用户已确认第二版在真我 GT Neo3 / Android 14 上流畅运行；第三版的启动效果尚待该手机验证。未进行完整通关、所有结局或所有 Android 版本验证。

## 版权与许可

见 [NOTICE.md](NOTICE.md)、[web/NOTICE.txt](web/NOTICE.txt) 与 [web/licenses](web/licenses)。原游戏、引擎和第三方组件各自保留原版权与许可；公开本工程不改变原游戏的权利归属。
