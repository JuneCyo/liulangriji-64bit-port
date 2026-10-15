const fs = require('fs');
const path = require('path');
const { Transform } = require('stream');
const browserify = require('./js-build/node_modules/browserify');
const terser = require('./js-build/node_modules/terser');
const root = path.resolve(__dirname, '..');
const engine = path.join(root, '.tools/cocos/cocos-engine-ada2855dbeb5c2913a4f44d2947854daea9aa3f5');
const output = path.join(root, 'web/cocos2d-js-min.js');
const defines = { CC_EDITOR: false, CC_PREVIEW: false, CC_BUILD: true, CC_TEST: false,
  CC_DEV: false, CC_DEBUG: false, CC_JSB: false, CC_WECHATGAME: false, CC_QQPLAY: false, CC_SUPPORT_JIT: true };

function preprocess(file) {
  if (path.extname(file) !== '.js') return new Transform({ transform(chunk, _, cb) { cb(null, chunk); } });
  const chunks = [];
  return new Transform({
    transform(chunk, _, cb) { chunks.push(chunk); cb(); },
    flush(cb) {
      let source = Buffer.concat(chunks).toString('utf8');
      if (path.basename(file) === 'CCView.js') {
        const hook = 'enableAutoFullScreen: function(enabled) {';
        if (!source.includes(hook)) { cb(new Error('Fullscreen compatibility hook not found')); return; }
        source = source.replace(hook, hook + ' return;');
      }
      terser.minify(source, {
        parse: { bare_returns: true },
        compress: { defaults: false, global_defs: defines, dead_code: true, conditionals: true, evaluate: true },
        mangle: false,
        format: { beautify: true, comments: /^!|Copyright|Permission|licensed/i }
      }).then(result => { this.push(result.code); cb(); }, cb);
    }
  });
}

const bundler = browserify({ entries: [path.join(engine, 'index.js')], detectGlobals: false,
  bundleExternal: false, debug: false,
  prelude: fs.readFileSync(path.join(engine, 'gulp/browserify_prelude.js'), 'utf8') });
bundler.exclude(path.join(engine, 'package.json'));
bundler.transform(preprocess);
bundler.bundle(async (error, buffer) => {
  if (error) { console.error(error); process.exitCode = 1; return; }
  try {
    const result = await terser.minify(buffer.toString(), {
      compress: { defaults: false, global_defs: defines, dead_code: true, conditionals: true, evaluate: true },
      mangle: false, format: { comments: /^!|Copyright|Permission|licensed/i }
    });
    fs.mkdirSync(path.dirname(output), { recursive: true });
    const androidCompatibility = '\n;(function(){if(window.StrayDiaryAndroid){var run=cc.game.run;cc.game.run=function(config,start){config.renderMode=1;config.frameRate=60;return run.call(this,config,start);};}if(window.StrayDiaryPort){window.StrayDiaryPort.installStartup(cc);}})();\n';
    fs.writeFileSync(output, result.code + androidCompatibility, 'utf8');
    console.log(`Web engine built: ${output}, ${Buffer.byteLength(result.code + androidCompatibility)} bytes`);
  } catch (error) { console.error(error); process.exitCode = 1; }
});
