import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'metrics'))
import pit_metrics as m
spec=importlib.util.spec_from_file_location('metrics_server',ROOT/'mcp/server.py');server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
ID='11111111-1111-4111-8111-111111111111'
class MetricsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'private/events.sqlite3'
 def test_metadata_only_and_hook_link_dedup(self):
  result={'structuredContent':{'entries':[{'excerpt':'private ž🙂','id':'secret hash'}]},'_meta':{'the-pit/metrics_event_id':ID}}
  m.record(ID,'pit_search',result,12,self.path)
  event={'hook_event_name':'PostToolUse','session_id':ID,'tool_use_id':'call1','turn_id':'turn1','tool_name':'mcp__pit__pit_search','tool_input':{'query':'secret query'},'tool_response':result}
  m.observe(event,self.path);m.observe(event,self.path)
  report=m.report(self.path);self.assertEqual(report['linked_observations'],1);self.assertEqual(next(t for t in report['tools'] if t['tool']=='pit_search')['returned_characters'],len('private ž🙂'))
  with m.connect(self.path) as db:
   dump='\n'.join(db.iterdump());self.assertNotIn('private ž',dump);self.assertNotIn('secret',dump)
  self.assertEqual(self.path.stat().st_mode&0o777,0o600)
  self.assertEqual(self.path.parent.stat().st_mode&0o777,0o700)
 def test_missing_meta_is_visible_unlinked(self):
  m.observe({'hook_event_name':'PostToolUse','session_id':ID,'tool_use_id':'call','tool_name':'mcp__pit__pit_append','tool_response':{}},self.path)
  self.assertEqual(m.report(self.path)['linked_observations'],1)
  self.assertEqual(m.report(self.path)['tools'][0]['latency_samples'],0)
 def test_hosted_array_result_and_unknown_latency(self):
  response={'content':[{'type':'text','text':json.dumps([{'excerpt':'secret ž🙂','id':'private'}])}], '_meta':{'the-pit/duration_ms':42,'the-pit/metrics_event_id':ID}}
  event={'hook_event_name':'PostToolUse','session_id':ID,'turn_id':'turn','tool_use_id':'call','tool_name':'mcp__codex_apps__the_pit.pit_search','tool_response':response}
  m.observe(event,self.path);m.observe(event,self.path)
  tool=next(t for t in m.report(self.path)['tools'] if t['tool']=='pit_search')
  self.assertEqual(tool['calls'],1);self.assertEqual(tool['returned_characters'],len('secret ž🙂'));self.assertEqual(tool['latency_ms_p50'],42)
 def test_capture_not_counted_as_harness(self):
  m.record(ID,'pit_append',{'structuredContent':{'verified':True,'inserted':True}},10,self.path,origin='automatic_capture',transport='hosted')
  self.assertEqual(m.report(self.path)['tools'][0]['calls'],0)
 def test_dispatch_metrics_failure_does_not_change_success(self):
  result={'content':[],'structuredContent':{'entries':[]},'isError':False}
  with patch.object(server,'call_tool',return_value=result),patch.object(server.pit_metrics,'record',side_effect=OSError('secret')):
   response=server.dispatch({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'pit_search','arguments':{'query':'secret'}}})
  self.assertEqual(response['result'],result)
 def test_failed_call_has_no_text_or_error_details(self):
  m.record(ID,'pit_append',{'isError':True,'content':[{'text':'secret'}]},1,self.path,origin='harness')
  report=m.report(self.path);self.assertEqual(report['tools'][0]['errors'],1)
  self.assertEqual(report['tools'][0]['verified_writes'],0)
if __name__=='__main__':unittest.main()
