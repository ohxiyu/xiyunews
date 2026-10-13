import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import vm from 'node:vm';
import {minifyAssets} from '../scripts/minify_edge_assets.mjs';
test('generated assets shrink while public behavior and legal notice survive',async()=>{
  const root=await mkdtemp(join(tmpdir(),'xiyunews-minify-'));
  try{
    await mkdir(join(root,'assets/js'),{recursive:true});await mkdir(join(root,'assets/css'),{recursive:true});
    await writeFile(join(root,'assets/js/bmtnews-ui.js'),'/*! Copyright fixture owner */\n(function () { const value = 42; window.answer = function () { return value; }; })();\n');
    await writeFile(join(root,'assets/css/bmtnews-ui.css'),'/*! Copyright fixture owner */\n.card { color: #ffffff; padding: 10px 10px 10px 10px; }\n');
    const result=await minifyAssets(root);
    assert.equal(result.files,2);assert.ok(result.after_bytes<result.before_bytes);
    const code=await readFile(join(root,'assets/js/bmtnews-ui.js'),'utf8');
    const context={window:{}};vm.runInNewContext(code,context);assert.equal(context.window.answer(),42);
    assert.ok(code.includes('Copyright fixture owner'));
    assert.ok((await readFile(join(root,'assets/css/bmtnews-ui.css'),'utf8')).includes('Copyright fixture owner'));
  }finally{await rm(root,{recursive:true,force:true});}
});
