(function () {
  'use strict';
  var keys = ['userData', 'data2', 'dataCopy'];
  var panel = document.getElementById('menu-panel');
  var toggle = document.getElementById('menu-toggle');
  var fileInput = document.getElementById('save-file');
  var toastTimer;
  function hasSave() {
    try { return !!JSON.parse(localStorage.getItem('userData')); }
    catch (error) { return false; }
  }
  if (hasSave()) document.getElementById('splash').style.backgroundImage = "url('startup-menu-continue.png')";
  function dismissNativeStartup() {
    if (window.StrayDiaryAndroid && window.StrayDiaryAndroid.startupReady) window.StrayDiaryAndroid.startupReady(hasSave());
  }
  function installStartup(engine) {
    var run = engine.game.run;
    engine.game.run = function (config, start) {
      return run.call(this, config, function () {
        engine.director.once(engine.Director.EVENT_AFTER_SCENE_LAUNCH, function () {
          engine.director.once(engine.Director.EVENT_AFTER_DRAW, function () {
            // Let WebView present the game canvas before removing its native cover.
            requestAnimationFrame(function () { requestAnimationFrame(function () {
              document.documentElement.classList.add('startup-ready');
              window.StrayDiaryPort.ready = true;
              dismissNativeStartup();
            }); });
          });
        });
        return start.apply(this, arguments);
      });
    };
  }
  function sizeGame() {
    var width = Math.max(1, Math.min(window.innerWidth, (window.innerHeight - 34) * 9 / 16));
    var frame = document.getElementById('GameDiv');
    frame.style.width = width + 'px';
    frame.style.height = width * 16 / 9 + 'px';
  }
  sizeGame();
  window.addEventListener('resize', sizeGame);
  function toast(message) {
    var status = document.getElementById('port-status');
    status.textContent = message;
    status.style.display = 'block';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { status.style.display = 'none'; }, 4500);
  }
  function closeMenu() { panel.style.display = 'none'; toggle.setAttribute('aria-expanded', 'false'); }
  function fatal(message) {
    var element = document.getElementById('fatal');
    element.hidden = false;
    element.textContent = '加载遇到问题：' + message + '\n请保留此信息以便排查。';
    dismissNativeStartup();
  }
  window.addEventListener('error', function (event) {
    if (document.getElementById('splash').style.display !== 'none') fatal(event.message || '资源加载失败');
  });
  window.addEventListener('unhandledrejection', function (event) {
    if (document.getElementById('splash').style.display !== 'none') fatal(String(event.reason));
  });
  toggle.onclick = function () {
    var open = panel.style.display !== 'block';
    panel.style.display = open ? 'block' : 'none';
    toggle.setAttribute('aria-expanded', String(open));
  };
  function exportSave() {
    var data = {};
    keys.forEach(function (key) {
      var value = localStorage.getItem(key);
      if (value !== null) data[key] = JSON.parse(value);
    });
    if (!Object.keys(data).length) { toast('暂无存档，请先开始游戏。'); return; }
    var text = JSON.stringify({ format: 'stray-diary-save', version: 1, exportedAt: new Date().toISOString(), data: data }, null, 2);
    var name = '流浪日记存档-' + new Date().toISOString().slice(0, 10) + '.json';
    if (window.StrayDiaryAndroid && window.StrayDiaryAndroid.exportSave) {
      window.StrayDiaryAndroid.exportSave(text, name);
    } else {
      var url = URL.createObjectURL(new Blob([text], { type: 'application/json;charset=utf-8' }));
      var a = document.createElement('a'); a.href = url; a.download = name; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      toast('存档已导出。');
    }
    closeMenu();
  }
  function validateData(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('存档内容无效');
    var names = Object.keys(data);
    if (!names.length || names.some(function (name) { return keys.indexOf(name) < 0; })) throw new Error('存档字段不匹配');
    names.forEach(function (name) {
      if (!data[name] || typeof data[name] !== 'object' || Array.isArray(data[name])) throw new Error('存档数据无效');
    });
    if (data.userData && (!Array.isArray(data.userData.itemNum) || !data.userData.role || typeof data.userData.role.hp !== 'number')) {
      throw new Error('不是可识别的流浪日记进度');
    }
    if (data.data2 && !Array.isArray(data.data2.gameData)) throw new Error('成就存档格式无效');
    return data;
  }
  function importSave(text) {
    try {
      if (typeof text !== 'string' || text.length > 5 * 1024 * 1024) throw new Error('存档文件过大');
      var parsed = JSON.parse(text);
      if (parsed.format !== 'stray-diary-save' || parsed.version !== 1) throw new Error('存档文件格式不匹配');
      var data = validateData(parsed.data);
      if (!window.confirm('导入将覆盖本设备当前存档，是否继续？')) return;
      var previous = {};
      keys.forEach(function (key) { previous[key] = localStorage.getItem(key); });
      try {
        keys.forEach(function (key) {
          if (Object.prototype.hasOwnProperty.call(data, key)) localStorage.setItem(key, JSON.stringify(data[key]));
          else localStorage.removeItem(key);
        });
      } catch (error) {
        keys.forEach(function (key) {
          if (previous[key] === null) localStorage.removeItem(key); else localStorage.setItem(key, previous[key]);
        });
        throw error;
      }
      location.reload();
    } catch (error) { toast('导入失败：' + error.message); }
  }
  document.getElementById('export-save').onclick = function () {
    try { exportSave(); } catch (error) { toast('导出失败：' + error.message); }
  };
  document.getElementById('import-save').onclick = function () {
    closeMenu();
    if (window.StrayDiaryAndroid && window.StrayDiaryAndroid.importSave) window.StrayDiaryAndroid.importSave();
    else { fileInput.value = ''; fileInput.click(); }
  };
  fileInput.onchange = function () {
    var file = fileInput.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast('存档文件过大。'); return; }
    var reader = new FileReader();
    reader.onload = function () { importSave(String(reader.result)); };
    reader.onerror = function () { toast('无法读取存档文件。'); };
    reader.readAsText(file);
  };
  window.StrayDiaryPort = { importSave: importSave, toast: toast, installStartup: installStartup,
    startupTimedOut: function () { if (!this.ready) fatal('启动耗时较长，请稍候；若持续无响应，请重新打开应用。'); } };
})();
