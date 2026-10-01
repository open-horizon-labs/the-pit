import {loadEnv} from 'vite';
const env=loadEnv('production', process.cwd(), 'VITE_');
const url=process.env.VITE_SUPABASE_URL || env.VITE_SUPABASE_URL;
const key=process.env.VITE_SUPABASE_PUBLISHABLE_KEY || env.VITE_SUPABASE_PUBLISHABLE_KEY;
if(url!=='https://iunbpyiylsbkscjaisid.supabase.co' || !key?.startsWith('sb_publishable_')) {
 console.error('Deployment requires the Intake project URL and its browser-safe sb_publishable_ key. Configure .env.production.local; never use a secret/service-role key.');
 process.exit(1);
}
