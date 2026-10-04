/// <reference types="vite/client" />
import { createClient, type Provider } from '@supabase/supabase-js';
import './style.css';
const root = document.querySelector<HTMLElement>('#app')!;
function text(tag: string, value: string) { const e = document.createElement(tag); e.textContent = value; root.append(e); return e; }
function button(label: string, action: () => Promise<void>) { const b = document.createElement('button'); b.textContent = label; root.append(b); b.onclick = async () => { b.disabled = true; try { await action(); } catch { text('p', 'Unable to complete this step. Please retry.'); } finally { b.disabled = false; } }; return b; }
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
text('h1', 'The Pit');
const footer=document.createElement('nav');footer.setAttribute('aria-label','Information');for(const [label,path] of [['About','/'],['Support','/support'],['Privacy','/privacy'],['Terms','/terms']]){const a=document.createElement('a');a.textContent=label;a.href=path;footer.append(a);}root.append(footer);
const info:Record<string,string[]>={
 '/support':['Support','The Pit is operated by Open Horizon Labs. Contact pit@urch.eu for support or privacy requests.','Save exact text through The Pit plugin in ChatGPT or Codex. Search uses literal phrases; range reads expand useful matches.','Export your text or erase all saved SaaS Pit text from your signed-in account page. Erasure is permanent in the live database. It does not delete your shared sign-in identity or any separate personal Pit. For help, contact us from your account email; we verify ownership before processing requests.'],
 '/privacy':['Privacy policy','Effective 1 October 2026. Operator: Open Horizon Labs. Contact: pit@urch.eu.','What we collect: account email and identity, exact text you choose to save, its content hash and first receipt time. We use these to authenticate you, preserve text, deduplicate it and return the passages you request. We do not classify text or require its source.','Supabase provides authentication and database storage. Cloudflare hosts the website and MCP endpoint. When you connect ChatGPT or Codex, requested excerpts are returned to that application under its own data practices. These service providers process data to operate the service; hosting may involve international transfers.','We retain saved text until you erase it or request erasure. Erasure removes it from the live SaaS database; provider backups can retain historical copies until their configured retention expires. Downloads and copies already returned to connected applications are outside our control. Account identity remains in our shared authentication service until separately resolved through support.','There is no application logging of saved text, search queries or access tokens. Cloudflare and Supabase may retain security and operational records under their provider policies. Temporary per-user request counters protect service availability. We do not sell your text or use it for advertising.','Controls: export from the signed-in account page, erase saved text there, revoke connected applications through your client, or contact pit@urch.eu for access, correction, deletion and other privacy requests. We verify account ownership. Only share text you are authorized to send; do not store authentication secrets, payment card details, protected health information or government identifiers.'],
 '/terms':['Terms of service','Effective 1 October 2026. The Pit is provided by Open Horizon Labs. Contact: pit@urch.eu.','The Pit stores and retrieves the exact text you choose to save. You retain rights to your text and authorize us to process it to operate the service and deliver your requested reads. You must have permission to share it.','Each account initially has 1 GiB of saved-text storage. Exact duplicate text uses no additional allowance. Hosted requests are throttled; service and transport limits also apply. We may adjust allowances with notice. Accepted text is never silently truncated.','Do not use the service unlawfully, bypass access controls, interfere with availability or store passwords, API keys, payment card details, protected health information or government identifiers. Connected tools act within the access you authorize.','Tools read and append. Erasure is a separate action on the signed-in account page and cannot be undone. Export important text and retain your own copy. Erasure affects the live SaaS corpus; provider backups and copies in other applications have separate retention.','We aim to provide reliable service but do not promise uninterrupted availability or suitability for a particular purpose. To the extent permitted by applicable law, the service is provided as available; nothing in these terms removes rights or remedies that applicable law requires.','We may restrict access to address abuse, security incidents or legal requirements. Material changes to these terms or discontinuation will be announced on the service with reasonable notice where practicable. Contact support about account closure, disputes or privacy requests.']};
async function main() {
 if(info[location.pathname]){for(const [i,line] of info[location.pathname].entries())text(i===0?'h2':'p',line);return;}
 if (!url || !key) { text('p', 'This installation is awaiting account configuration.'); return; }
 const client = createClient(url, key, { auth: { flowType: 'pkce', detectSessionInUrl: false } });
 const params = new URLSearchParams(location.search);
 const authorizationId = params.get('authorization_id');
 // Only our fixed consent route survives sign-in. Caller-supplied return URLs are never followed.
 const destination = authorizationId ? '/oauth/consent?'+new URLSearchParams({authorization_id:authorizationId}) : '/';
 if (location.pathname === '/auth/callback') {
  const code = params.get('code');
  if (!code) throw new Error('Missing code');
  const {error} = await client.auth.exchangeCodeForSession(code);
  if (error) throw error;
  history.replaceState(null, '', destination);
 }
 const {data, error} = await client.auth.getUser();
 if (error && data.user) throw error;
 if (!data.user) {
  text('h2', 'Keep useful work within reach');
  text('p', 'Sign in to save text and connect your AI tools.');
  const allowed = new Set(['google', 'github']);
  const providers = String(import.meta.env.VITE_LOGIN_PROVIDERS || '').split(',').filter(p => allowed.has(p));
  for (const provider of providers) button('Continue with '+(provider === 'google' ? 'Google' : 'GitHub'), async () => {
   const callback = new URL('/auth/callback', location.origin);
   if (authorizationId) callback.searchParams.set('authorization_id', authorizationId);
   const {error} = await client.auth.signInWithOAuth({provider:provider as Provider,options:{redirectTo:callback.href}});
   if (error) throw error;
  });
  const form = document.createElement('form');
  const email = document.createElement('input'); email.type='email'; email.placeholder='Email address'; email.required=true; email.autocomplete='email'; email.setAttribute('aria-label','Email address');
  const send=document.createElement('button'); send.textContent='Email me a sign-in link';
  form.append(email,send); root.append(form);
  form.onsubmit=async event=>{event.preventDefault();send.disabled=true;try{
   const callback=new URL('/auth/callback',location.origin);if(authorizationId)callback.searchParams.set('authorization_id',authorizationId);
   const {error}=await client.auth.signInWithOtp({email:email.value,options:{emailRedirectTo:callback.href}});
   text('p',error?'Unable to send a sign-in link. Please retry.':'Check your email for a sign-in link.');
  }catch{text('p','Unable to send a sign-in link. Please retry.');}finally{send.disabled=false;}};
  const reviewer=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Sign in with a password';reviewer.append(summary);const passwordForm=document.createElement('form');const passwordEmail=document.createElement('input');passwordEmail.type='email';passwordEmail.required=true;passwordEmail.autocomplete='username';passwordEmail.placeholder='Email address';passwordEmail.setAttribute('aria-label','Account email');const password=document.createElement('input');password.type='password';password.required=true;password.autocomplete='current-password';password.placeholder='Password';password.setAttribute('aria-label','Password');const submit=document.createElement('button');submit.textContent='Sign in';passwordForm.append(passwordEmail,password,submit);reviewer.append(passwordForm);root.append(reviewer);
  passwordForm.onsubmit=async event=>{event.preventDefault();submit.disabled=true;try{const {error}=await client.auth.signInWithPassword({email:passwordEmail.value,password:password.value});password.value='';if(error)text('p','Sign-in failed. Check your account details.');else location.assign(destination);}catch{text('p','Sign-in failed. Please retry.');}finally{submit.disabled=false;}};
  return;
 }
 text('p', 'Signed in as '+data.user.email);
 if (authorizationId) {
  const {data:details,error}=await client.auth.oauth.getAuthorizationDetails(authorizationId);
  if(error || !details) throw error || new Error('Invalid authorization');
  if ('redirect_url' in details) { location.assign(details.redirect_url); return; }
  text('h2','Connect '+details.client.name);
  text('p','Only continue if you intended to connect this application.');
  text('p','Requested identity permissions: '+details.scope);
  text('p','Return destination: '+new URL(details.redirect_uri).origin);
  text('p','This application can read and append exact text in your private Pit, including search, range reads and enumeration. It cannot edit or delete entries.');
  const trustedClients=String(import.meta.env.VITE_PIT_CLIENT_IDS || '').split(',').filter(Boolean);
  const allow = button('Allow connection',async()=>{const {error}=await client.auth.oauth.approveAuthorization(authorizationId);if(error)throw error;});
  if (!trustedClients.includes(details.client.id)) { allow.disabled=true; text('p','This client has not been configured for Pit access. Connection approval is unavailable.'); }
  button('Cancel',async()=>{const {error}=await client.auth.oauth.denyAuthorization(authorizationId);if(error)throw error;});
 } else {
  text('h2','Your private Pit');text('p','Connect The Pit in ChatGPT or Codex to save text and recover context.');
  button('Export my text',async()=>{
   const {data:{session}}=await client.auth.getSession();if(!session)throw new Error('Sign in required');
   const chunks:BlobPart[]=[];let after:string|undefined;
   for(;;){
    let query=client.from('pit_entries').select('id,received_at,content').order('id').limit(10);if(after)query=query.gt('id',after);
    const {data:rows,error}=await query;if(error)throw error;
    if(!rows?.length)break;
    for(const row of rows)chunks.push(JSON.stringify(row)+'\n');
    after=rows[rows.length-1].id;
   }
   const blob=new Blob(chunks,{type:'application/x-ndjson'});const download=URL.createObjectURL(blob);const a=document.createElement('a');a.href=download;a.download='the-pit-export.ndjson';a.click();setTimeout(()=>URL.revokeObjectURL(download),1000);text('p','Export downloaded. Entries appended during export may require another export.');
  });
  if(import.meta.env.VITE_PIT_ACCOUNT_ERASURE==='enabled')button('Erase all my saved text',async()=>{
   if(!confirm('Permanently erase all text in your SaaS Pit? This cannot be undone. Your shared sign-in account and personal Pit are not deleted.'))return;
   const {data:count,error}=await client.rpc('pit_erase_my_data');if(error)throw error;text('p','Erased '+count+' entries from your SaaS Pit.');
  });
  else text('p','Account data erasure is being prepared before public release. It will erase your SaaS Pit without deleting accounts or data belonging to other Intake services.');
 }
 button('Sign out',async()=>{const {error}=await client.auth.signOut();if(error)throw error;location.reload();});
}
main().catch(()=>text('p','This sign-in or connection request could not be verified. Start again from the application you want to connect.'));
