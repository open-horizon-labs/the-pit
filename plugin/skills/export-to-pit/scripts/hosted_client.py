"""Use the installed hosted app through native saved authentication; never read tokens."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from pit_support import PitError, DeliveryUnknown

class Client:
    def __init__(self,timeout=30):
        self.timeout=timeout;self.process=None;self.identity=0;self.buffer=b''
    def rpc(self,method,params):
        self.identity+=1;identity=self.identity
        self.process.stdin.write((json.dumps({'jsonrpc':'2.0','id':identity,'method':method,'params':params},ensure_ascii=False)+'\n').encode());self.process.stdin.flush()
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            if b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1)
                message=json.loads(line)
                if message.get('id')==identity:
                    if 'error' in message:raise PitError('Hosted Pit native request failed; no operation confirmed')
                    return message['result']
                # No model turns, permission changes or unsolicited requests are authorized here.
                if 'id' in message and 'method' in message:
                    self.process.stdin.write((json.dumps({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32000,'message':'Interactive approval required'}})+'\n').encode());self.process.stdin.flush()
                continue
            if not self.selector.select(max(0,deadline-time.monotonic())):break
            block=os.read(self.process.stdout.fileno(),65536)
            if not block:raise PitError('Hosted Pit native connection closed')
            self.buffer+=block
        raise DeliveryUnknown('Hosted Pit response unconfirmed; recover using the saved text and hash')
    def start(self):
        if self.process:return
        self.process=subprocess.Popen(['codex','app-server','--stdio'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        self.rpc('initialize',{'clientInfo':{'name':'pit_local_capture','version':'0.1.0'},'capabilities':{'experimentalApi':True}})
        self.process.stdin.write(b'{"jsonrpc":"2.0","method":"initialized"}\n');self.process.stdin.flush()
        # Ephemeral transport context only: no conversation or model turn is created/persisted.
        result=self.rpc('thread/start',{'cwd':str(Path.home()),'ephemeral':True})
        self.thread=result['thread']['id']
    def call(self,tool,args):
        self.start()
        result=self.rpc('mcpServer/tool/call',{'threadId':self.thread,'server':'codex_apps','tool':'the_pit.'+tool,'arguments':args})
        if result.get('isError'):raise PitError('Hosted Pit tool failed; no successful operation confirmed')
        if isinstance(result.get('structuredContent'),(dict,list)):return result['structuredContent']
        for block in result.get('content',[]):
            if block.get('type')=='text':
                try:return json.loads(block['text'])
                except (ValueError,KeyError):continue
        raise PitError('Hosted Pit returned an unsupported receipt')
    def append(self,content):
        result=self.call('pit_append',{'content':content})
        identity=hashlib.sha256(content.encode('utf-8')).hexdigest()
        if not isinstance(result,dict) or result.get('id')!=identity or result.get('verified') is not True:
            raise DeliveryUnknown('Hosted Pit exact-text receipt unconfirmed')
        return {**result,'uploaded':True,'destination':'hosted'}
    def search(self,query,limit=5,context=500):return self.call('pit_search',{'query':query,'limit':limit,'context':context})
    def search_page(self,query,limit=20,context=500,before_received_at=None,before_id=None):
        args={'query':query,'limit':limit,'context':context}
        if before_received_at is not None or before_id is not None:
            args.update(before_received_at=before_received_at,before_id=before_id)
        return self.call('pit_search_page',args)
    def read_range(self,identity,start=0,end=1000):return self.call('pit_read_range',{'id':identity,'start':start,'end':end})
    def verify(self,content):
        identity=hashlib.sha256(content.encode('utf-8')).hexdigest()
        # Exact bounded reads, no stdout of corpus text.
        for start in range(0,len(content),20000):
            rows=self.read_range(identity,start,min(len(content),start+20000))
            if not rows:return {'id':identity,'found':False,'verified':False}
            if rows[0]['excerpt']!=content[start:start+20000]:raise PitError('Hosted text mismatch')
        return {'id':identity,'found':True,'verified':True}
    def close(self):
        if self.process:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.selector.close();self.process=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--append-file',type=Path);mode.add_argument('--verify-file',type=Path)
    parser.add_argument('--request-timeout',type=float,default=30)
    args=parser.parse_args()
    try:
        with Client(args.request_timeout) as client:
            content=(args.append_file or args.verify_file).read_bytes().decode('utf-8')
            result=client.append(content) if args.append_file else client.verify(content)
        print(json.dumps(result))
    except (PitError,OSError,ValueError,KeyError,TypeError):
        print('Hosted Pit delivery unconfirmed; private snapshot remains available.',file=sys.stderr);sys.exit(1)
