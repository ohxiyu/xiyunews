import {cp, mkdir, writeFile} from 'node:fs/promises';
const origin=process.env.API_ORIGIN||'';
if(origin && new URL(origin).protocol!=='https:') throw new Error('API_ORIGIN must use HTTPS');
await mkdir('dist',{recursive:true});
await cp('public','dist',{recursive:true});
await writeFile('dist/config.js',`window.FOMOBTC_CONFIG=${JSON.stringify({apiOrigin:origin,revision:process.env.SOURCE_COMMIT||'unknown'})};\n`);
