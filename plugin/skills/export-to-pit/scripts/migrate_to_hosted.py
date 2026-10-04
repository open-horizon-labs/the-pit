"""Copy the original personal corpus into the connected hosted Pit; retain originals."""
import json
import os
from pathlib import Path
import urllib.parse
from pit_client import Client as LegacyClient,save_config
from hosted_client import Client
import time,uuid,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'metrics'))
import pit_metrics

def main():
 root=Path.home()/'.local/share/the-pit/migration';root.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(root,0o700)
 ledger=root/'hosted-copy.json';state=json.loads(ledger.read_text()) if ledger.exists() else {'verified':{},'complete':False}
 legacy=LegacyClient();count=0;bytes_saved=0;after=None
 with Client() as hosted:
  while True:
   query={'select':'id,content','order':'id.asc','limit':10}
   if after:query['id']='gt.'+after
   rows=legacy.api('entries?'+urllib.parse.urlencode(query))
   if not rows:break
   for row in rows:
    after=row['id']
    if after in state['verified']:continue
    started=time.monotonic();receipt=hosted.append(row['content'])
    if receipt['id']!=after:raise RuntimeError('Exact identity mismatch')
    state['verified'][after]={'received_at':receipt['received_at'],'inserted':receipt['inserted']}
    save_config(state,ledger)
    try:pit_metrics.record(str(uuid.uuid4()),'pit_append',{'structuredContent':receipt},(time.monotonic()-started)*1000,origin='migration',transport='hosted')
    except Exception:pass
    count+=1;bytes_saved+=len(row['content'].encode('utf-8'))
    if count%10==0:print(json.dumps({'copied_this_run':count,'bytes_this_run':bytes_saved}),flush=True)
 state['complete']=True;save_config(state,ledger)
 print(json.dumps({'complete':True,'verified_entries':len(state['verified']),'copied_this_run':count,'bytes_this_run':bytes_saved,'originals_retained':True}),flush=True)
if __name__=='__main__':main()
