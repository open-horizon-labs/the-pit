/// <reference types="vite/client" />
import { createClient, type Provider } from '@supabase/supabase-js';
import './style.css';
const root = document.querySelector<HTMLElement>('#app')!;
function text(tag: string, value: string) { const e = document.createElement(tag); e.textContent = value; root.append(e); return e; }
function button(label: string, action: () => Promise<void>) { const b = document.createElement('button'); b.textContent = label; root.append(b); b.onclick = async () => { b.disabled = true; try { await action(); } catch { text('p', 'Unable to complete this step. Please retry.'); } finally { b.disabled = false; } }; return b; }
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
text('h1', 'The Pit');
async function main() {
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
 } else { text('h2','Your account is ready'); text('p','Plugin connection setup is being prepared.'); }
 button('Sign out',async()=>{const {error}=await client.auth.signOut();if(error)throw error;location.reload();});
}
main().catch(()=>text('p','This sign-in or connection request could not be verified. Start again from the application you want to connect.'));
