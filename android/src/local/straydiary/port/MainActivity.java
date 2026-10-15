package local.straydiary.port;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.graphics.Color;
import android.graphics.BitmapFactory;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.Gravity;
import android.view.WindowInsets;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.JsResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Locale;

/** Offline host for the original game's recovered Web build. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String HOME = "https://" + HOST + "/index.html";
    private static final int EXPORT = 101;
    private static final int IMPORT = 102;
    private static final int MAX_SAVE_BYTES = 5 * 1024 * 1024;
    private WebView web;
    private String pendingExport;
    private View startupCover;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(34, 34, 34));
        web = new WebView(this);
        WebView.setWebContentsDebuggingEnabled((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0);
        // Keep the window's hardware acceleration; a software WebView layer copies
        // the entire game surface on every frame and delays touch/animation updates.
        web.setBackgroundColor(Color.rgb(34, 34, 34));
        root.addView(web, new FrameLayout.LayoutParams(-1, -1));
        showStartupCover(root);
        setContentView(root);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            if (Build.VERSION.SDK_INT >= 30) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            } else {
                view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                        insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            }
            return insets;
        });
        root.requestApplyInsets();
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setSupportZoom(false);
        settings.setTextZoom(100);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        web.addJavascriptInterface(new SaveBridge(), "StrayDiaryAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost()) || !"GET".equals(request.getMethod())) {
                    return errorResponse(403, "Forbidden");
                }
                String asset = uri.getPath();
                if (asset == null || asset.equals("/")) asset = "/index.html";
                asset = asset.substring(1);
                for (String part : asset.split("/")) {
                    if (part.equals("..") || part.indexOf('\\') >= 0 || part.indexOf('\0') >= 0) return errorResponse(403, "Forbidden");
                }
                try {
                    return new WebResourceResponse(mime(asset), "UTF-8", 200, "OK",
                            Collections.singletonMap("Cache-Control", "no-store"), getAssets().open(asset));
                } catch (Exception failure) {
                    Log.e("StrayDiary", "Missing asset: " + asset);
                    return errorResponse(404, "Not Found");
                }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost());
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage message) {
                if (message.messageLevel() == ConsoleMessage.MessageLevel.ERROR) {
                    Log.e("StrayDiary", message.message() + " @ " + message.sourceId() + ":" + message.lineNumber());
                }
                return true;
            }
            @Override public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this).setMessage(message)
                        .setPositiveButton("继续", (dialog, which) -> result.confirm())
                        .setNegativeButton("取消", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel()).show();
                return true;
            }
        });
        web.loadUrl(HOME);
        web.postDelayed(() -> {
            if (startupCover != null) {
                dismissStartupCover();
                web.evaluateJavascript("window.StrayDiaryPort && window.StrayDiaryPort.startupTimedOut()", null);
            }
        }, 12000);
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void showStartupCover(FrameLayout root) {
        boolean upgraded = false;
        try {
            android.content.pm.PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            upgraded = info.lastUpdateTime > info.firstInstallTime;
        } catch (Exception ignored) { }
        boolean hasSave = getPreferences(MODE_PRIVATE).getBoolean("startupHasSave", upgraded);
        try (InputStream stream = getAssets().open(hasSave ? "startup-menu-continue.png" : "startup-menu.png")) {
            LinearLayout cover = new LinearLayout(this);
            cover.setOrientation(LinearLayout.VERTICAL);
            cover.setBackgroundColor(Color.rgb(34, 34, 34));
            cover.setClickable(true);
            FrameLayout bar = new FrameLayout(this);
            bar.setBackgroundColor(Color.rgb(244, 244, 244));
            TextView title = new TextView(this);
            title.setText("流浪日记"); title.setTextSize(12); title.setTextColor(Color.rgb(85, 85, 85));
            title.setGravity(Gravity.CENTER_VERTICAL); title.setPadding(dp(12), 0, 0, 0);
            bar.addView(title, new FrameLayout.LayoutParams(-1, -1));
            TextView saves = new TextView(this);
            saves.setText("存档"); saves.setTextSize(13); saves.setTextColor(Color.rgb(68, 68, 68));
            saves.setGravity(Gravity.CENTER); saves.setPadding(dp(16), 0, dp(16), 0);
            bar.addView(saves, new FrameLayout.LayoutParams(-2, -1, Gravity.RIGHT));
            View border = new View(this); border.setBackgroundColor(Color.rgb(204, 204, 204));
            bar.addView(border, new FrameLayout.LayoutParams(-1, dp(1), Gravity.BOTTOM));
            cover.addView(bar, new LinearLayout.LayoutParams(-1, dp(34)));
            ImageView menu = new ImageView(this);
            menu.setScaleType(ImageView.ScaleType.FIT_CENTER);
            menu.setImageBitmap(BitmapFactory.decodeStream(stream));
            cover.addView(menu, new LinearLayout.LayoutParams(-1, 0, 1));
            startupCover = cover;
            root.addView(cover, new FrameLayout.LayoutParams(-1, -1));
        } catch (Exception failure) { Log.e("StrayDiary", "Startup cover unavailable", failure); }
    }

    private void dismissStartupCover() {
        if (startupCover == null) return;
        ((android.view.ViewGroup) startupCover.getParent()).removeView(startupCover);
        startupCover = null;
    }

    private static String mime(String name) {
        String value = name.toLowerCase(Locale.ROOT);
        if (value.endsWith(".html")) return "text/html";
        if (value.endsWith(".js")) return "application/javascript";
        if (value.endsWith(".json")) return "application/json";
        if (value.endsWith(".css")) return "text/css";
        if (value.endsWith(".png")) return "image/png";
        if (value.endsWith(".jpg") || value.endsWith(".jpeg")) return "image/jpeg";
        if (value.endsWith(".mp3")) return "audio/mpeg";
        if (value.endsWith(".ogg")) return "audio/ogg";
        return "application/octet-stream";
    }

    private static WebResourceResponse errorResponse(int status, String reason) {
        return new WebResourceResponse("text/plain", "UTF-8", status, reason, Collections.emptyMap(),
                new ByteArrayInputStream(reason.getBytes(StandardCharsets.UTF_8)));
    }

    private final class SaveBridge {
        @JavascriptInterface public void startupReady(boolean hasSave) {
            runOnUiThread(() -> {
                getPreferences(MODE_PRIVATE).edit().putBoolean("startupHasSave", hasSave).apply();
                dismissStartupCover();
            });
        }
        @JavascriptInterface public void exportSave(String text, String filename) {
            if (text == null || text.length() > MAX_SAVE_BYTES) return;
            runOnUiThread(() -> {
                if (pendingExport != null) return;
                pendingExport = text;
                Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("application/json");
                intent.putExtra(Intent.EXTRA_TITLE, "流浪日记存档.json");
                try { startActivityForResult(intent, EXPORT); }
                catch (Exception failure) { pendingExport = null; notifyUser("无法打开文件保存窗口"); }
            });
        }
        @JavascriptInterface public void importSave() {
            runOnUiThread(() -> {
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try { startActivityForResult(intent, IMPORT); }
                catch (Exception failure) { notifyUser("无法打开文件选择窗口"); }
            });
        }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == EXPORT) {
            String text = pendingExport;
            pendingExport = null;
            if (result != RESULT_OK || data == null || data.getData() == null || text == null) return;
            try (OutputStream stream = getContentResolver().openOutputStream(data.getData())) {
                if (stream == null) throw new Exception("No output stream");
                stream.write(text.getBytes(StandardCharsets.UTF_8));
                notifyUser("存档已导出");
            } catch (Exception failure) { notifyUser("存档导出失败"); }
        } else if (request == IMPORT && result == RESULT_OK && data != null && data.getData() != null) {
            try (InputStream stream = getContentResolver().openInputStream(data.getData());
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                if (stream == null) throw new Exception("No input stream");
                byte[] buffer = new byte[8192];
                int n;
                while ((n = stream.read(buffer)) != -1) {
                    if (out.size() + n > MAX_SAVE_BYTES) throw new Exception("Save too large");
                    out.write(buffer, 0, n);
                }
                String text = new String(out.toByteArray(), StandardCharsets.UTF_8);
                web.evaluateJavascript("window.StrayDiaryPort.importSave(" + JSONObject.quote(text) + ");", null);
            } catch (Exception failure) { notifyUser("存档读取失败，请选择有效的 JSON 存档"); }
        }
    }

    private void notifyUser(String text) { Toast.makeText(this, text, Toast.LENGTH_LONG).show(); }

    @Override protected void onPause() {
        super.onPause();
        if (web != null) {
            web.evaluateJavascript("!!localStorage.getItem('userData')", value ->
                    getPreferences(MODE_PRIVATE).edit().putBoolean("startupHasSave", "true".equals(value)).apply());
            web.onPause();
        }
    }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override public void onBackPressed() {
        new AlertDialog.Builder(this).setMessage("退出流浪日记？")
                .setPositiveButton("退出", (dialog, which) -> finish())
                .setNegativeButton("继续游戏", null).show();
    }
    @Override protected void onDestroy() {
        if (web != null) { web.removeJavascriptInterface("StrayDiaryAndroid"); web.destroy(); }
        super.onDestroy();
    }
}
