"""Passive metadata only. Never record tool inputs, text, hashes or error messages."""
import json
import os
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone

DEFAULT = Path.home()/'.local/share/the-pit/metrics/events.sqlite3'
TOOLS = {'pit_search','pit_read_range','pit_append','pit_list'}

def connect(path=DEFAULT):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.parent.is_symlink() or path.is_symlink():
        raise OSError('Unsafe metrics path')
    os.chmod(path.parent,0o700)
    fd=os.open(path,os.O_CREAT|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
    os.chmod(path,0o600)
    db=sqlite3.connect(path,timeout=0.2)
    db.execute('CREATE TABLE IF NOT EXISTS calls (event_id TEXT PRIMARY KEY, at TEXT, tool TEXT, outcome TEXT, duration_ms REAL, hits INTEGER, returned_chars INTEGER, verified INTEGER, inserted INTEGER, session_id TEXT, turn_id TEXT, tool_use_id TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS observations (session_id TEXT, tool_use_id TEXT, turn_id TEXT, tool TEXT, at TEXT, linked INTEGER, PRIMARY KEY(session_id,tool_use_id))')
    columns={r[1] for r in db.execute('PRAGMA table_info(calls)')}
    for name in ['origin','transport']:
        if name not in columns:db.execute('ALTER TABLE calls ADD COLUMN '+name+' TEXT')
    return db

def record(event_id,tool,result,duration_ms,path=DEFAULT,origin="legacy",transport="local"):
    if tool not in TOOLS:return
    data=decode_result(result)
    rows=data if isinstance(data,list) else data.get('entries',[])
    receipt=data if isinstance(data,dict) else {}
    success=not result.get('isError',False)
    hits=len(rows) if success and tool=='pit_search' else None
    chars=sum(len(r.get('excerpt',r.get('content',''))) for r in rows) if success and tool!='pit_append' else None
    verified=int(receipt.get('verified') is True) if success and tool=='pit_append' else None
    inserted=int(receipt['inserted']) if success and type(receipt.get('inserted')) is bool else None
    with connect(path) as db:
        db.execute('INSERT OR IGNORE INTO calls(event_id,at,tool,outcome,duration_ms,hits,returned_chars,verified,inserted,origin,transport) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (event_id,datetime.now(timezone.utc).isoformat(),tool,'success' if success else 'error',duration_ms,hits,chars,verified,inserted,origin,transport))

def decode_result(response):
    structured=response.get('structuredContent')
    if isinstance(structured,(dict,list)):return structured
    for block in response.get('content',[]):
        if isinstance(block,dict) and block.get('type')=='text':
            try:
                parsed=json.loads(block['text'])
                if isinstance(parsed,(dict,list)):return parsed
            except (ValueError,KeyError):pass
    return {}

def tool_name(name):
    for prefix in ['mcp__pit__','mcp__pit_hosted__','mcp__codex_apps__the_pit_','mcp__codex_apps__the_pit.']:
        if isinstance(name,str) and name.startswith(prefix) and name[len(prefix):] in TOOLS:return name[len(prefix):]
    return None

def observe(event,path=DEFAULT,origin="harness",at=None,duration_override=None):
    import uuid
    if event.get('hook_event_name')!='PostToolUse':return
    name=event.get('tool_name','');tool=tool_name(name)
    if not tool:return
    session=str(uuid.UUID(event['session_id']))
    call=event.get('tool_use_id');turn=event.get('turn_id')
    if not isinstance(call,str) or not 1<=len(call)<=200:return
    if turn is not None and (not isinstance(turn,str) or len(turn)>200):return
    response=event.get('tool_response',{})
    if isinstance(response,str):response=json.loads(response)
    if not isinstance(response,dict):return
    meta=response.get('_meta',{}) or {}
    identity=str(uuid.uuid5(uuid.NAMESPACE_URL,session+':'+call))
    duration=meta.get('the-pit/duration_ms')
    if duration_override is not None:duration=duration_override
    if type(duration) not in (int,float) or not 0<=duration<3600000:duration=None
    transport='local' if name.startswith('mcp__pit__') else 'hosted'
    record(identity,tool,response,duration,path,origin=origin,transport=transport)
    with connect(path) as db:
        db.execute("UPDATE calls SET session_id=?,turn_id=?,tool_use_id=?,origin=CASE WHEN origin='harness' THEN 'harness' ELSE ? END,transport=? WHERE event_id=? AND tool=?",
                   (session,turn,call,origin,transport,identity,tool))
        if duration_override is not None:db.execute('UPDATE calls SET duration_ms=? WHERE event_id=?',(duration,identity))
        if at:db.execute('UPDATE calls SET at=? WHERE event_id=?',(at,identity))
        db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?)',(session,call,turn,tool,at or datetime.now(timezone.utc).isoformat(),1))

def report(path=DEFAULT):
    if not Path(path).exists():return {'calls':0,'hook_observations':0}
    with connect(path) as db:
        tools=[]
        for tool in sorted(TOOLS):
            rows=db.execute("SELECT outcome,duration_ms,hits,returned_chars,verified,inserted FROM calls WHERE tool=? AND origin='harness'",(tool,)).fetchall()
            times=sorted(r[1] for r in rows if r[1] is not None)
            tools.append({'tool':tool,'calls':len(rows),'errors':sum(r[0]=='error' for r in rows),'latency_samples':len(times),
                'latency_ms_p50':times[(len(times)-1)//2] if times else None,
                'latency_ms_p95':times[min(len(times)-1,int(len(times)*.95))] if times else None,
                'empty_searches':sum(r[2]==0 for r in rows),'returned_characters':sum(r[3] or 0 for r in rows),
                'verified_writes':sum(r[4] or 0 for r in rows),'duplicate_writes':sum(r[5]==0 for r in rows)})
        sessions=[{'session_id':r[0],'searches':r[1],'range_reads':r[2],'writes':r[3]} for r in db.execute("SELECT session_id,SUM(tool='pit_search'),SUM(tool='pit_read_range'),SUM(tool='pit_append') FROM calls WHERE origin='harness' GROUP BY session_id")]
        return {'tools':tools,'historical_tools':[{'tool':r[0],'calls':r[1],'errors':r[2],'returned_characters':r[3] or 0} for r in db.execute("SELECT tool,COUNT(*),SUM(outcome='error'),SUM(returned_chars) FROM calls WHERE origin='historical' GROUP BY tool")], 'counts_by_origin':[{'origin':r[0] or 'legacy','calls':r[1]} for r in db.execute('SELECT origin,COUNT(*) FROM calls GROUP BY origin')],'completed_harness_calls':db.execute("SELECT COUNT(*) FROM calls WHERE origin='harness'").fetchone()[0],
                'sessions_with_search_then_range':db.execute("SELECT COUNT(DISTINCT r.session_id) FROM calls r WHERE r.origin='harness' AND r.tool='pit_read_range' AND EXISTS(SELECT 1 FROM calls s WHERE s.origin='harness' AND s.session_id=r.session_id AND s.tool='pit_search' AND s.at<r.at)").fetchone()[0],
                'linked_observations':db.execute('SELECT COUNT(*) FROM observations WHERE linked=1').fetchone()[0], 'sessions':sessions}

if __name__=='__main__':
    if '--hook' in sys.argv:
        try:observe(json.load(sys.stdin))
        except Exception:pass
        print('{}')
    else:print(json.dumps(report(),indent=2))
