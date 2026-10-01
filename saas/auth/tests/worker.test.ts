import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair, SignJWT, createLocalJWKSet, exportJWK} from 'jose';
import worker, {verifyCaller,makeHandler} from '../worker/index.ts';
const env={SUPABASE_URL:'https://iunbpyiylsbkscjaisid.supabase.co',SUPABASE_PUBLISHABLE_KEY:'sb_publishable_test',PIT_CLIENT_IDS:'trusted',ASSETS:{fetch:async()=>new Response('site')}};
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
 const list=await call({jsonrpc:'2.0',id:2,method:'tools/list',params:{}});assert.equal(list.status,200);assert.deepEqual((await decode(list)).result.tools.map((t:any)=>t.name).sort(),['pit_append','pit_list','pit_read_range','pit_search']);await handler.close();
});
