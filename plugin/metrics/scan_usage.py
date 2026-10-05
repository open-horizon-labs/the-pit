"""Incrementally derive Pit metrics from completed local harness tool records only."""
import json
import os
from pathlib import Path
import sys
import uuid
from pit_metrics import observe,DEFAULT
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/export-to-pit/scripts'))
from export_session import locate_rollout
from pit_support import save_config
STATE=Path.home()/'.local/share/the-pit/metrics/scan-state'

def scan(path,session,path_db=DEFAULT,state_root=STATE,origin='harness',max_bytes=32*1024*1024):
 session=str(uuid.UUID(session));path=Path(path)
 state_root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(state_root,0o700)
 state_file=state_root/(session+'.json')
 state=json.loads(state_file.read_text()) if state_file.exists() else {'offset':0}
 size=path.stat().st_size
 if origin=='historical':state.setdefault('historical_until',size)
 if state['offset']>size:raise ValueError('Transcript truncated; coverage unknown')
 with path.open('rb') as stream:
  identity=json.loads(stream.readline())
  if identity.get('type')!='session_meta' or identity.get('payload',{}).get('id')!=session:raise ValueError('Wrong transcript identity')
  stream.seek(state['offset']);raw=stream.read(max_bytes)
 end=raw.rfind(b'\n')+1
 if end==0 and raw:raise ValueError('Incomplete or oversized transcript record')
 count=0
 position=state['offset']
 for line in raw[:end].splitlines(keepends=True):
  record_origin='historical' if position<state.get('historical_until',0) else origin
  position+=len(line)
  record=json.loads(line);payload=record.get('payload',{})
  if record.get('type')!='event_msg' or payload.get('type')!='item_completed':continue
  item=payload.get('item',{})
  if item.get('type')!='McpToolCall':continue
  server=item.get('server');tool=item.get('tool','')
  if server=='codex_apps' and tool.startswith('the_pit.'):name='mcp__codex_apps__'+tool
  elif server in ('pit','pit_hosted') and tool in ('pit_query','pit_search','pit_read_range','pit_append','pit_list'):name='mcp__'+server+'__'+tool
  else:continue
  from pit_metrics import tool_name
  if not tool_name(name):continue
  if item.get('status') not in ('completed','failed'):raise ValueError('Unsupported tool completion status')
  result=item.get('result') or {}
  if not isinstance(result,dict):raise ValueError('Unsupported tool result format')
  if item['status']=='failed':result={**result,'isError':True}
  duration=item.get('duration');ms=None
  if isinstance(duration,dict) and type(duration.get('secs')) is int and type(duration.get('nanos')) is int:
   ms=duration['secs']*1000+duration['nanos']/1e6
  observe({'hook_event_name':'PostToolUse','session_id':session,'tool_use_id':item['id'],'turn_id':payload.get('turn_id'),
           'tool_name':name,'tool_response':result},path_db,origin=record_origin,at=record.get('timestamp'),duration_override=ms)
  count+=1
 state.update(offset=state['offset']+end,complete=state['offset']+end>=size,observed=count)
 save_config(state,state_file)
 return state

def current(event):
 if event.get('hook_event_name') not in ('Stop','PreCompact'):raise ValueError('Unsupported hook event')
 session=event['session_id'];root=Path(os.environ.get('CODEX_HOME','~/.codex')).expanduser()
 # Exact host session only; no newest-file fallback and no supplied cross-session path.
 return scan(locate_rollout(root,session),session)

if __name__=='__main__':
 try:
  if '--backfill' in sys.argv:
   root=Path(os.environ.get('CODEX_HOME','~/.codex')).expanduser();sessions=0;calls=0;gaps=0
   for folder in ('sessions','archived_sessions'):
    for p in (root/folder).rglob('rollout-*.jsonl'):
     try:
      with p.open('rb') as stream:r=json.loads(stream.readline())
      session=r.get('payload',{}).get('id')
      # Skip unsupported layouts and retain explicit coverage gaps.
      state=scan(p,session,origin='historical');sessions+=1;calls+=state['observed'];gaps+=not state['complete']
     except (ValueError,OSError,KeyError,TypeError):gaps+=1
   print(json.dumps({'sessions_scanned':sessions,'pit_calls_observed':calls,'coverage_gaps':gaps,'origin':'historical'}))
  else:
   state=current(json.load(sys.stdin))
   print('{}' if state['complete'] else json.dumps({'systemMessage':'Pit metrics coverage is incomplete; pending transcript records remain.'}))
 except Exception:
  print(json.dumps({'systemMessage':'Pit metrics transcript coverage is unavailable; do not interpret missing counts as zero usage.'}))
