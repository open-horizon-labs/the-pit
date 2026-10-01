"""Passive metadata only. Never record tool inputs, text, hashes or error messages."""
import json
import os
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone

DEFAULT = Path.home()/'.local/share/the-pit/metrics/events.sqlite3'
TOOLS = {'pit_search','pit_read_range','pit_append'}

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
    return db

def record(event_id,tool,result,duration_ms,path=DEFAULT):
    if tool not in TOOLS:return
    data=result.get('structuredContent',{})
    rows=data.get('entries',[])
    success=not result.get('isError',False)
    hits=len(rows) if success and tool=='pit_search' else None
    chars=sum(len(r.get('excerpt',r.get('content',''))) for r in rows) if success and tool!='pit_append' else None
    verified=int(data.get('verified') is True) if success and tool=='pit_append' else None
    inserted=int(data['inserted']) if success and type(data.get('inserted')) is bool else None
    with connect(path) as db:
        db.execute('INSERT OR IGNORE INTO calls(event_id,at,tool,outcome,duration_ms,hits,returned_chars,verified,inserted) VALUES(?,?,?,?,?,?,?,?,?)',
                   (event_id,datetime.now(timezone.utc).isoformat(),tool,'success' if success else 'error',duration_ms,hits,chars,verified,inserted))

def observe(event,path=DEFAULT):
    import uuid
    if event.get('hook_event_name')!='PostToolUse':return
    name=event.get('tool_name','')
    if name not in {'mcp__pit__'+t for t in TOOLS}:return
    session=str(uuid.UUID(event['session_id']))
    call=event.get('tool_use_id')
    turn=event.get('turn_id')
    if not isinstance(call,str) or not 1<=len(call)<=200:return
    if turn is not None and (not isinstance(turn,str) or len(turn)>200):return
    response=event.get('tool_response',{})
    if isinstance(response,str):response=json.loads(response)
    identity=response.get('_meta',{}).get('the-pit/metrics_event_id') if isinstance(response,dict) else None
    with connect(path) as db:
        linked=False
        if isinstance(identity,str):
            try:identity=str(uuid.UUID(identity))
            except ValueError:identity=None
            if identity:
                linked=db.execute('UPDATE calls SET session_id=?,turn_id=?,tool_use_id=? WHERE event_id=? AND tool=?',
                    (session,turn,call,identity,name.removeprefix('mcp__pit__'))).rowcount==1
        db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?)',(session,call,turn,name.removeprefix('mcp__pit__'),datetime.now(timezone.utc).isoformat(),int(linked)))

def report(path=DEFAULT):
    if not Path(path).exists():return {'calls':0,'hook_observations':0}
    with connect(path) as db:
        tools=[]
        for tool in sorted(TOOLS):
            rows=db.execute('SELECT outcome,duration_ms,hits,returned_chars,verified,inserted FROM calls WHERE tool=?',(tool,)).fetchall()
            times=sorted(r[1] for r in rows)
            tools.append({'tool':tool,'calls':len(rows),'errors':sum(r[0]=='error' for r in rows),
                'latency_ms_p50':times[(len(times)-1)//2] if times else None,
                'latency_ms_p95':times[min(len(times)-1,int(len(times)*.95))] if times else None,
                'empty_searches':sum(r[2]==0 for r in rows),'returned_characters':sum(r[3] or 0 for r in rows),
                'verified_writes':sum(r[4] or 0 for r in rows),'duplicate_writes':sum(r[5]==0 for r in rows)})
        sessions=[{'session_id':r[0],'searches':r[1],'range_reads':r[2],'writes':r[3]} for r in db.execute("SELECT session_id,SUM(tool='pit_search'),SUM(tool='pit_read_range'),SUM(tool='pit_append') FROM observations GROUP BY session_id")]
        return {'tools':tools,'hook_observations':db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],
                'sessions_with_search_then_range':db.execute("SELECT COUNT(DISTINCT r.session_id) FROM observations r WHERE r.tool='pit_read_range' AND EXISTS(SELECT 1 FROM observations s WHERE s.session_id=r.session_id AND s.tool='pit_search' AND s.at<r.at)").fetchone()[0],
                'linked_observations':db.execute('SELECT COUNT(*) FROM observations WHERE linked=1').fetchone()[0], 'sessions':sessions}

if __name__=='__main__':
    if '--hook' in sys.argv:
        try:observe(json.load(sys.stdin))
        except Exception:pass
        print('{}')
    else:print(json.dumps(report(),indent=2))
