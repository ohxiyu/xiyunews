// Optimize generated copies of owned UI assets. Original source stays readable.
import {createRequire} from 'node:module';
import {readFile,writeFile,lstat} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const require=createRequire(new URL('../ops/daily-dispatcher/package.json',import.meta.url));
const {transform}=require('esbuild');
const OWNED=['css/core.css','js/core.js'];
export async function minifyAssets(root){
  if((await lstat(root)).isSymbolicLink())throw Error('symlink output root');
  let before=0,after=0,files=0;
  for(const relative of OWNED){
    const path=join(root,'assets',relative);
    let info;try{info=await lstat(path);}catch(error){if(error.code==='ENOENT')continue;throw error;}
    if(info.isSymbolicLink()||!info.isFile())throw Error('unsafe generated asset');
    const original=await readFile(path,'utf8');
    const result=await transform(original,{loader:relative.endsWith('.css')?'css':'js',
      minify:true,target:'es2020',charset:'utf8',legalComments:'inline'});
    before+=Buffer.byteLength(original);after+=Buffer.byteLength(result.code);files++;
    await writeFile(path,result.code);
  }
  return {files,before_bytes:before,after_bytes:after};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(!process.argv[2])throw Error('generated output directory required');
  console.log(JSON.stringify(await minifyAssets(resolve(process.argv[2]))));
}
