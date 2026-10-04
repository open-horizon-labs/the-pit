import json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'metrics'))
import scan_usage as s
import pit_metrics as m
ID='11111111-1111-4111-8111-111111111111'
class ScannerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
  self.file=root/'rollout.jsonl';self.db=root/'metrics/events.sqlite3';self.state=root/'state'
  self.file.write_text(json.dumps({'type':'session_meta','payload':{'id':ID}})+'\n')
 def append(self,status='completed'):
  result={'content':[{'type':'text','text':json.dumps([{'excerpt':'private text','id':'secret hash'}])}], '_meta':{'the-pit/duration_ms':4}}
  item={'type':'McpToolCall','server':'codex_apps','tool':'the_pit.pit_search','id':'call1','arguments':{'query':'private query'},'status':status,'result':result,'duration':{'secs':1,'nanos':500000000}}
  with self.file.open('a') as f:f.write(json.dumps({'timestamp':'2026-10-04T08:00:00Z','type':'event_msg','payload':{'type':'item_completed','item':item}})+'\n')
  return result
 def scan(self,origin='harness'):return s.scan(self.file,ID,self.db,self.state,origin)
 def test_incremental_dedup_and_privacy(self):
  result=self.append();m.observe({'hook_event_name':'PostToolUse','session_id':ID,'tool_use_id':'call1','tool_name':'mcp__codex_apps__the_pit.pit_search','tool_response':result},self.db)
  self.assertTrue(self.scan()['complete']);self.assertEqual(self.scan()['observed'],0)
  tool=next(t for t in m.report(self.db)['tools'] if t['tool']=='pit_search')
  self.assertEqual(tool['calls'],1);self.assertEqual(tool['latency_ms_p50'],1500)
  with m.connect(self.db) as db:self.assertNotIn('private','\n'.join(db.iterdump()));self.assertNotIn('secret','\n'.join(db.iterdump()))
 def test_historical_is_separate(self):
  self.append();self.scan('historical');report=m.report(self.db)
  self.assertEqual(report['completed_harness_calls'],0);self.assertEqual(report['historical_tools'][0]['calls'],1);self.assertEqual(report['sessions'],[])
 def test_pending_history_keeps_boundary(self):
  self.append();size=self.file.stat().st_size
  s.scan(self.file,ID,self.db,self.state,origin='historical',max_bytes=len(self.file.read_bytes().splitlines(keepends=True)[0]))
  self.scan()
  report=m.report(self.db)
  self.assertEqual(report['completed_harness_calls'],0);self.assertEqual(report['historical_tools'][0]['calls'],1)
 def test_truncation_and_wrong_identity_fail(self):
  self.append();self.scan();self.file.write_text('')
  with self.assertRaises(ValueError):self.scan()
 def test_partial_record_pending(self):
  with self.file.open('a') as f:f.write('{')
  self.assertFalse(self.scan()['complete'])
 def test_unsupported_completion_fails(self):
  self.append('mystery')
  with self.assertRaises(ValueError):self.scan()
if __name__=='__main__':unittest.main()
