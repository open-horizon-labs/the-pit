\set ON_ERROR_STOP on
begin;
insert into public.pit_oauth_clients values ('trusted', true);
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"11111111-1111-1111-1111-111111111111","client_id":"trusted"}',true);
do $$ declare r record; begin
 select * into r from public.pit_saas_append(E'Exact 🦊\n  whitespace');
 if not r.inserted or not r.verified then raise exception 'First append failed'; end if;
 select * into r from public.pit_saas_append(E'Exact 🦊\n  whitespace');
 if r.inserted or not r.verified then raise exception 'Duplicate failed'; end if;
 perform public.pit_saas_append('Account A only');
 if (select count(*) from public.pit_saas_search('whitespace')) <> 1 then raise exception 'Search failed';end if;
 if (select excerpt from public.pit_saas_read_range(encode(extensions.digest(E'Exact 🦊\n  whitespace','sha256'),'hex'),6,7)) <> '🦊' then raise exception 'Unicode range failed';end if;
end $$;
select set_config('request.jwt.claims','{"sub":"22222222-2222-2222-2222-222222222222","client_id":"trusted"}',true);
do $$ declare r record; begin
 if exists(select from public.pit_saas_search('Account A')) then raise exception 'Cross tenant search leak';end if;
 if exists(select from public.pit_saas_read_range(encode(extensions.digest('Account A only','sha256'),'hex'))) then raise exception 'Cross tenant range leak';end if;
 select * into r from public.pit_saas_append(E'Exact 🦊\n  whitespace');
 if not r.inserted or not r.verified then raise exception 'Tenant dedup leak';end if;
 if (select count(*) from public.pit_saas_list()) <> 1 then raise exception 'List leak';end if;
 begin update public.pit_entries set content='bad';raise exception 'Update allowed';exception when insufficient_privilege then null;end;
 begin delete from public.pit_entries;raise exception 'Delete allowed';exception when insufficient_privilege then null;end;
 begin insert into public.pit_entries(user_id,content) values('11111111-1111-1111-1111-111111111111','bad');raise exception 'Ownership spoof allowed';exception when insufficient_privilege then null;end;
end $$;
select set_config('request.jwt.claims','{"sub":"22222222-2222-2222-2222-222222222222","client_id":"untrusted"}',true);
do $$ begin
 if exists(select from public.pit_entries) then raise exception 'Untrusted client reads';end if;
 begin perform public.pit_saas_append('bad');raise exception 'Untrusted client writes';exception when insufficient_privilege then null;end;
end $$;
reset role;
set local role anon;
do $$ begin
 begin perform public.pit_saas_search('Exact');raise exception 'Anonymous RPC allowed';exception when insufficient_privilege then null;end;
end $$;
reset role;
set local role supabase_auth_admin;
do $$ declare r jsonb;begin
 r:=public.pit_access_token_hook('{"claims":{"aud":"authenticated","client_id":"trusted"}}');
 if r->'claims'->>'aud' <> 'https://pit.ohlabs.ai/mcp' then raise exception 'Audience hook failed';end if;
 r:=public.pit_access_token_hook('{"claims":{"aud":"authenticated"}}');
 if r->'claims'->>'aud' <> 'authenticated' then raise exception 'Ordinary auth changed';end if;
end $$;
reset role;
rollback;
select 'tenant isolation, exact dedup, Unicode ranges, privileges, client policy and hook passed' as result;
