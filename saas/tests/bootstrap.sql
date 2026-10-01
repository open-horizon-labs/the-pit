-- Disposable local PostgreSQL only. Minimal Supabase auth helpers.
create role anon; create role authenticated; create role supabase_auth_admin;
create schema auth; create schema extensions;
create extension pgcrypto with schema extensions;
create extension pg_trgm with schema extensions;
create table auth.users(id uuid primary key);
create function auth.jwt() returns jsonb language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb $$;
create function auth.uid() returns uuid language sql stable as $$ select (auth.jwt()->>'sub')::uuid $$;
grant usage on schema auth, extensions to authenticated, supabase_auth_admin;
grant execute on all functions in schema auth to authenticated;
insert into auth.users values ('11111111-1111-1111-1111-111111111111'), ('22222222-2222-2222-2222-222222222222');
