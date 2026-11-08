"""Acknowledge event-only publication; never acknowledge unrelated daily changes."""
import json
from pathlib import Path
import subprocess
from .publication_state import active_store

def main():
    store=active_store()
    if store is None:return
    subprocess.run(['git','fetch','--depth=1','origin','gh-pages'],check=True,capture_output=True)
    sha=subprocess.check_output(['git','rev-parse','FETCH_HEAD'],text=True).strip()
    values={}
    for filename,name in [('events.json','events'),('event-legacy-urls.json','event_urls')]:
        exported=Path('event-output/_data')/filename
        if not exported.exists():continue
        actual=subprocess.check_output(['git','show',sha+':_data/'+filename],text=True)
        if json.loads(actual)!=json.loads(exported.read_text()):raise ValueError('event checkpoint differs from generated output')
        values[name]=json.loads(actual)
    store.acknowledge_documents(values)
    print(json.dumps({'event_checkpoint':sha,'acknowledged':sorted(values)}))

if __name__=='__main__':main()
