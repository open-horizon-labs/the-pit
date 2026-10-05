import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair, SignJWT, createLocalJWKSet, exportJWK} from 'jose';
import worker, {verifyCaller,makeHandler,serveAuthenticated} from '../worker/index.ts';
const env={SUPABASE_URL:'https://iunbpyiylsbkscjaisid.supabase.co',SUPABASE_PUBLISHABLE_KEY:'sb_publishable_test',PIT_CLIENT_IDS:'trusted',PIT_RATE_LIMIT:{limit:async()=>({success:true})},ASSETS:{fetch:async()=>new Response('site')}};
test('discovery and unauthenticated boundary',async()=>{
 const d=await worker.fetch(new Request('https://pit.ohlabs.ai/.well-known/oauth-protected-resource/mcp'),env);assert.equal((await d.json()).resource,'https://pit.ohlabs.ai/mcp');
 const denied=await worker.fetch(new Request('https://pit.ohlabs.ai/mcp'),env);assert.equal(denied.status,401);assert.match(denied.headers.get('WWW-Authenticate')!,/resource_metadata/);
 assert.equal((await worker.fetch(new Request('https://pit.ohlabs.ai/mcp',{headers:{Origin:'https://evil.example'}}),env)).status,403);
 assert.equal((await worker.fetch(new Request('https://pit.ohlabs.ai/mcp',{headers:{Authorization:'Bearer malformed'}}),env)).status,401);
});
test('issuer, audience, expiry, role, client and signature enforced',async()=>{
 const {privateKey,publicKey}=await generateKeyPair('ES256');const jwk=await exportJWK(publicKey);jwk.kid='test';const ks=createLocalJWKSet({keys:[jwk]});
 const sign=(claims:Record<string,unknown>={})=>new SignJWT({role:'authenticated',client_id:'trusted',...claims}).setProtectedHeader({alg:'ES256',kid:'test'}).setSubject('11111111-1111-1111-1111-111111111111').setIssuedAt().setIssuer('https://iunbpyiylsbkscjaisid.supabase.co/auth/v1').setAudience('https://pit.ohlabs.ai/mcp').setExpirationTime('2m').sign(privateKey);
 assert.equal((await verifyCaller(await sign(),['trusted'],ks)).client_id,'trusted');
 await assert.rejects(verifyCaller(await sign({role:'service_role'}),['trusted'],ks));await assert.rejects(verifyCaller(await sign({client_id:'other'}),['trusted'],ks));
 for(const [issuer,aud,exp] of [['wrong','https://pit.ohlabs.ai/mcp','2m'],['https://iunbpyiylsbkscjaisid.supabase.co/auth/v1','authenticated','2m'],['https://iunbpyiylsbkscjaisid.supabase.co/auth/v1','https://pit.ohlabs.ai/mcp','-1m']]){
 const token=await new SignJWT({role:'authenticated',client_id:'trusted'}).setProtectedHeader({alg:'ES256',kid:'test'}).setSubject('11111111-1111-1111-1111-111111111111').setIssuedAt().setIssuer(issuer).setAudience(aud).setExpirationTime(exp).sign(privateKey);await assert.rejects(verifyCaller(token,['trusted'],ks));}
 const other=await generateKeyPair('ES256');const token=await new SignJWT({}).setProtectedHeader({alg:'ES256',kid:'test'}).sign(other.privateKey);await assert.rejects(verifyCaller(token,['trusted'],ks));
});
test('real SDK serves legacy initialize and tool discovery without DB call',async()=>{
 const handler=makeHandler(env,'test-token');
 const call=async(body:unknown)=>handler.fetch(new Request('https://pit.ohlabs.ai/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify(body)}));
 const decode=async(r:Response)=>{const text=await r.text();return JSON.parse(text.startsWith('event:') ? text.split('\n').find(l=>l.startsWith('data:'))!.slice(5) : text);};
 const init=await call({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'test',version:'1'}}});assert.equal(init.status,200);assert.equal((await decode(init)).result.serverInfo.name,'the-pit');
 const list=await call({jsonrpc:'2.0',id:2,method:'tools/list',params:{}});assert.equal(list.status,200);const tools=(await decode(list)).result.tools;assert.deepEqual(tools.map((t:any)=>t.name).sort(),['pit_append','pit_list','pit_query','pit_read_range','pit_search','pit_search_page']);for(const tool of tools){assert.equal(typeof tool.annotations.destructiveHint,'boolean');assert.equal(typeof tool.annotations.readOnlyHint,'boolean');assert.equal(tool.annotations.openWorldHint,false);}assert.equal(tools.find((t:any)=>t.name==='pit_query').annotations.readOnlyHint,true);await handler.close();
});

test('pit query forwards exact bounded scope to its dedicated authenticated RPC and preserves coverage',async()=>{
 const handler=makeHandler(env,'caller-token');const original=globalThis.fetch;const calls:any[]=[];
 globalThis.fetch=async(input:any,init:any)=>{calls.push({url:String(input),headers:init.headers,body:JSON.parse(String(init.body))});return new Response(JSON.stringify({entries:[{id:'a'.repeat(64),excerpt:'match'}],coverage:{candidate_limit:100,characters_per_entry:1000000,candidates_truncated:true,characters_truncated:false},offset_unit:'zero-based Unicode code points'}),{headers:{'Content-Type':'application/json'}});};
 const call=async(id:number,arguments_:unknown)=>{const response=await handler.fetch(new Request('https://pit.ohlabs.ai/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'pit_query',arguments:arguments_}})}));const text=await response.text();return JSON.parse(text.startsWith('event:')?text.split('\n').find(line=>line.startsWith('data:'))!.slice(5):text);};
 try{
  const result=await call(25,{terms:['exact','literal'],limit:7,entry_ids:['a'.repeat(64)],since:'2026-10-01T00:00:00Z',until:'2026-10-05T00:00:00+00:00'});
  assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/rest/v1/rpc/pit_saas_query'));assert.equal(calls[0].headers.Authorization,'Bearer caller-token');
  assert.deepEqual(calls[0].body,{p_terms:['exact','literal'],p_limit:7,p_entry_ids:['a'.repeat(64)],p_since:'2026-10-01T00:00:00Z',p_until:'2026-10-05T00:00:00+00:00'});
  assert.deepEqual(JSON.parse(result.result.content[0].text).coverage,{candidate_limit:100,characters_per_entry:1000000,candidates_truncated:true,characters_truncated:false});
  for(const invalid of [{terms:[]},{terms:['  ']},{terms:['x'],unknown:true},
   {terms:['x'],since:'2026-10-01T00:00:00Z',until:'2026-10-01T00:00:00Z'},
   {terms:['x'],since:'2026-10-05T00:00:00Z',until:'2026-10-01T00:00:00Z'},
   {terms:['🙂'.repeat(101)]}])await call(26,invalid);
  assert.equal(calls.length,1);
  await call(27,{terms:['🙂'.repeat(100)]});assert.equal(calls.length,2);
  assert.deepEqual(calls[1].body.p_terms,['🙂'.repeat(100)]);
 }finally{globalThis.fetch=original;await handler.close();}
});

test('generic search page forwards a paired receipt cursor to its dedicated RPC',async()=>{
 const handler=makeHandler(env,'test-token');const original=globalThis.fetch;const calls:any[]=[];
 globalThis.fetch=async(input:any,init:any)=>{calls.push({url:String(input),body:JSON.parse(String(init.body))});return new Response('[]',{headers:{'Content-Type':'application/json'}});};
 const call=async(id:number,arguments_:unknown)=>handler.fetch(new Request('https://pit.ohlabs.ai/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'pit_search_page',arguments:arguments_}})}));
 try{
  const valid=await call(21,{query:'literal phrase',limit:7,context:12,before_received_at:'2026-10-04T12:30:00+00:00',before_id:'a'.repeat(64)});assert.equal(valid.status,200);
  assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/rest/v1/rpc/pit_saas_search_page'));
  assert.deepEqual(calls[0].body,{p_query:'literal phrase',p_limit:7,p_context:12,p_before_received_at:'2026-10-04T12:30:00+00:00',p_before_id:'a'.repeat(64)});
  await call(22,{query:'literal phrase',before_id:'a'.repeat(64)});assert.equal(calls.length,1);
 }finally{globalThis.fetch=original;await handler.close();}
});

test('per-user throttle rejects before executing tools and fails closed',async()=>{
 const request=new Request('https://pit.ohlabs.ai/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id:4,method:'tools/call',params:{name:'pit_append',arguments:{content:'must not be saved'}}})});
 const keys:string[]=[];const denied={...env,PIT_RATE_LIMIT:{limit:async({key}:{key:string})=>{keys.push(key);return {success:false};}}};
 const original=globalThis.fetch;globalThis.fetch=async()=>{throw new Error('DB must not be called');};
 try{const result=await serveAuthenticated(request,denied,'private-token','owner');assert.equal(result.status,429);assert.equal(result.headers.get('Retry-After'),'60');assert.deepEqual(keys,['pit-user:owner']);assert.ok(!(await result.text()).includes('private-token'));
 const broken={...env,PIT_RATE_LIMIT:{limit:async()=>{throw new Error('binding unavailable');}}};assert.equal((await serveAuthenticated(request,broken,'private-token','owner')).status,503);
 }finally{globalThis.fetch=original;}
});

test('tool result includes content-free duration metadata on success and failure',async()=>{
 const handler=makeHandler(env,'private-token');const original=globalThis.fetch;
 const call=async(id:number)=>{const r=await handler.fetch(new Request('https://pit.ohlabs.ai/mcp',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json, text/event-stream'},body:JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'pit_search',arguments:{query:'private query'}}})}));const t=await r.text();return JSON.parse(t.startsWith('event:')?t.split('\n').find(l=>l.startsWith('data:'))!.slice(5):t).result;};
 try{
  globalThis.fetch=async()=>new Response('[]',{headers:{'Content-Type':'application/json'}});
  const success=await call(31);assert.ok(success._meta['the-pit/duration_ms']>=0);assert.match(success._meta['the-pit/metrics_event_id'],/^[a-f0-9-]{36}$/);assert.ok(!JSON.stringify(success._meta).includes('private'));
  globalThis.fetch=async()=>new Response('{}',{status:500});const failed=await call(32);assert.equal(failed.isError,true);assert.ok(failed._meta['the-pit/duration_ms']>=0);
 }finally{globalThis.fetch=original;await handler.close();}
});
