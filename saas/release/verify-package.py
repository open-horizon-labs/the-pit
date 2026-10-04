"""Verify the extracted package without repository imports, auth or real capture."""
import json,os,re,subprocess,sys,tempfile
from pathlib import Path
from zipfile import ZipFile
archive=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='pit-package-') as temporary:
 root=Path(temporary);package=root/'plugin'
 with ZipFile(archive) as z:
  names=z.namelist()
  assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
  assert not any(n.endswith(('pit_client.py','migrate_to_hosted.py','.sqlite3','.pyc')) or 'connection.json' in n for n in names)
  z.extractall(package)
 manifest=json.loads((package/'plugin.json').read_text());hooks=json.loads((package/'hooks/hooks.json').read_text())
 assert manifest['extensions']['com.openai']['hooks']=='./hooks/hooks.json'
 assert len(list((package/'skills').rglob('SKILL.md')))==3
 handlers=[h for groups in hooks['hooks'].values() for group in groups for h in group['hooks']]
 assert len(handlers)==5
 for h in handlers:
  match=re.search(r'\$\{PLUGIN_ROOT\}/([^\"]+)',h['command']);assert match and (package/match[1]).is_file()
 scripts=package/'skills/export-to-pit/scripts'
 # -I isolates import resolution; explicitly expose only extracted package folders.
 code="""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);state=Path(sys.argv[2])
sys.path[:0]=[str(root/'skills/export-to-pit/scripts'),str(root/'metrics'),str(root/'hooks')]
import hosted_client,export_session,pit_support,pit_metrics,scan_usage,precompact,retrieval_context
assert all(Path(m.__file__).resolve().is_relative_to(root.resolve()) for m in [hosted_client,export_session,pit_support,pit_metrics,scan_usage,precompact,retrieval_context])
session='11111111-1111-4111-8111-111111111111'
records=[{'type':'session_meta','payload':{'id':session}},
 {'type':'event_msg','payload':{'type':'item_completed','item':{'type':'UserMessage','id':'message1','content':[{'type':'text','text':'Private fixture ž🙂'}]}}},
 {'timestamp':'2026-10-04T00:00:00Z','type':'event_msg','payload':{'type':'item_completed','item':{'type':'McpToolCall','id':'call1','server':'codex_apps','tool':'the_pit.pit_search','status':'completed','arguments':{'query':'private query'},'result':{'structuredContent':[{'excerpt':'private retrieved text','id':'private hash'}]},'duration':{'secs':0,'nanos':500000000}}}}]
p=state/'fixture.jsonl';p.write_text(''.join(json.dumps(r)+'\\n' for r in records))
result=scan_usage.scan(p,session,state/'metrics/events.sqlite3',state/'cursors');assert result['complete']
scan_usage.scan(p,session,state/'metrics/events.sqlite3',state/'cursors')
report=pit_metrics.report(state/'metrics/events.sqlite3');assert report['completed_harness_calls']==1
with pit_metrics.connect(state/'metrics/events.sqlite3') as db:assert 'private' not in '\\n'.join(db.iterdump())
text,receipt=export_session.render_snapshot(p.read_bytes(),session);assert receipt['messages']==1 and 'ž🙂' in text.decode()
assert retrieval_context.run({'hook_event_name':'SessionStart','source':'startup','session_id':session})['continue']
print(json.dumps({'modules':7,'hook_handlers':5,'fixture_export_messages':1,'deduplicated_calls':1,'no_private_text_in_metrics':True}))
"""
 env=os.environ.copy();env.pop('PYTHONPATH',None)
 result=subprocess.run([sys.executable,'-I','-c',code,str(package),str(root)],cwd=root,env=env,text=True,capture_output=True)
 if result.returncode:raise RuntimeError(result.stderr)
 print(result.stdout.strip())
 # Exercise the shipped CLI directly with no source-tree working directory.
 result=subprocess.run([sys.executable,str(scripts/'export_session.py'),'--check','--rollout',str(root/'fixture.jsonl'),'--thread-id','11111111-1111-4111-8111-111111111111'],cwd=root,env=env,text=True,capture_output=True,check=True)
 assert json.loads(result.stdout)['status']=='validated'
 print(json.dumps({'archive':archive.name,'files':len(names),'export_cli':'validated','credentials_or_personal_state':'excluded'}))
