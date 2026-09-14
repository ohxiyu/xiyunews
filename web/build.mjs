import {writeFile} from 'node:fs/promises';
import {build} from 'vite';
const origin=process.env.API_ORIGIN||'';
if(origin && new URL(origin).protocol!=='https:')throw new Error('API_ORIGIN must use HTTPS');
await build();
await writeFile('dist/config.js',`window.FOMOBTC_CONFIG=${JSON.stringify({apiOrigin:origin,revision:process.env.SOURCE_COMMIT||'unknown'})};\n`);
