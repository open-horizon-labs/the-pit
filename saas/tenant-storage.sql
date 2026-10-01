-- SaaS corpus; existing personal public.entries is unchanged.
begin;
create table public.pit_entries (
 user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
 id text generated always as (encode(extensions.digest(content, 'sha256'), 'hex')) stored,
 received_at timestamptz not null default clock_timestamp(),
 content text not null,
 primary key (user_id, id)
);
alter table public.pit_entries enable row level security;
revoke all on public.pit_entries from public, anon, authenticated;
grant select on public.pit_entries to authenticated;
grant insert(content) on public.pit_entries to authenticated;
-- Public client identifiers only; administrator-managed, disabled by default.
create table public.pit_oauth_clients (client_id text primary key, enabled boolean not null default false);
alter table public.pit_oauth_clients enable row level security;
revoke all on public.pit_oauth_clients from public, anon, authenticated;
grant select on public.pit_oauth_clients to authenticated;
create policy pit_client_ids_read on public.pit_oauth_clients for select to authenticated using (true);
create policy pit_owner_read on public.pit_entries for select to authenticated using (
 user_id = (select auth.uid()) and (
 (select auth.jwt()->>'client_id') is null or exists (
 select 1 from public.pit_oauth_clients c where c.enabled and c.client_id = (select auth.jwt()->>'client_id'))));
create policy pit_owner_append on public.pit_entries for insert to authenticated with check (
 user_id = (select auth.uid()) and (
 (select auth.jwt()->>'client_id') is null or exists (
 select 1 from public.pit_oauth_clients c where c.enabled and c.client_id = (select auth.jwt()->>'client_id'))));
create index pit_entries_content_trgm_idx on public.pit_entries using gin(content extensions.gin_trgm_ops);
create index pit_entries_receipt_idx on public.pit_entries(user_id, received_at desc, id);
create or replace function public.pit_saas_search(
  p_query text, p_limit integer default 5, p_context integer default 500
)
returns table (
  id text, received_at timestamptz, total_characters integer,
  match_start integer, match_end integer,
  start_char integer, end_char integer, excerpt text
)
language plpgsql stable security invoker set search_path = ''
as $function$
declare
  v_pattern text;
begin
  if p_query is null or pg_catalog.char_length(p_query) not between 1 and 1000
     or p_limit is null or p_limit not between 1 and 20
     or p_context is null or p_context not between 0 and 2000 then
    raise exception 'Invalid search parameters' using errcode = '22023';
  end if;
  -- PostgreSQL's literal director treats every query character as ordinary text.
  -- Use the identical pattern/case rules for the indexed predicate and offsets.
  v_pattern := '***=' || p_query;
  return query
  with candidates as materialized (
    select e.id, e.received_at, e.content
    from public.pit_entries e
    where e.content operator(pg_catalog.~*) v_pattern
    order by e.received_at desc, e.id
    limit p_limit
  ), located as materialized (
    select c.*, pg_catalog.char_length(c.content) as size,
      pg_catalog.regexp_instr(c.content, v_pattern, 1, 1, 0, 'i') - 1 as first,
      pg_catalog.regexp_instr(c.content, v_pattern, 1, 1, 1, 'i') - 1 as last
    from candidates c
  ), bounded as (
    select l.*, greatest(0, l.first - p_context) as lo,
      least(l.size, l.last + p_context) as hi
    from located l where l.first >= 0 and l.last > l.first
  )
  select b.id, b.received_at, b.size, b.first, b.last, b.lo, b.hi,
    pg_catalog.substr(b.content, b.lo + 1, b.hi - b.lo)
  from bounded b order by b.received_at desc, b.id;
end;
$function$;

create or replace function public.pit_saas_read_range(
  p_id text, p_start integer default 0, p_end integer default 1000
)
returns table (
  id text, received_at timestamptz, total_characters integer,
  start_char integer, end_char integer, excerpt text
)
language plpgsql stable security invoker set search_path = ''
as $function$
begin
  if p_id is null or p_id !~ '^[a-f0-9]{64}$'
     or p_start is null or p_end is null or p_start < 0 or p_end < p_start
     or p_end::bigint - p_start::bigint > 20000 then
    raise exception 'Invalid range parameters' using errcode = '22023';
  end if;
  return query
  with sized as materialized (
    select e.id, e.received_at, e.content, pg_catalog.char_length(e.content) as size
    from public.pit_entries e where e.id = p_id
  ), bounded as (
    select s.*, least(p_start, s.size) as lo, least(p_end, s.size) as hi from sized s
  )
  select b.id, b.received_at, b.size, b.lo, b.hi,
    pg_catalog.substr(b.content, b.lo + 1, b.hi - b.lo)
  from bounded b;
end;
$function$;

revoke all on function public.pit_saas_search(text, integer, integer) from public, anon;
revoke all on function public.pit_saas_read_range(text, integer, integer) from public, anon;
grant execute on function public.pit_saas_search(text, integer, integer) to authenticated;
grant execute on function public.pit_saas_read_range(text, integer, integer) to authenticated;
create function public.pit_saas_append(p_content text)
returns table(id text, received_at timestamptz, inserted boolean, verified boolean)
language plpgsql security invoker set search_path = '' as $$
declare hash text; was_inserted boolean;
begin
 if p_content is null then raise exception 'Text is required' using errcode='22023'; end if;
 hash := encode(extensions.digest(p_content, 'sha256'), 'hex');
 insert into public.pit_entries(content) values(p_content) on conflict do nothing;
 was_inserted := found;
 return query select e.id, e.received_at, was_inserted, e.content = p_content
 from public.pit_entries e where e.user_id = auth.uid() and e.id = hash;
end;
$$;
create function public.pit_saas_list(p_after text default null, p_limit integer default 25)
returns table(id text, received_at timestamptz, total_characters integer)
language plpgsql stable security invoker set search_path = '' as $$
begin
 if p_limit is null or p_limit not between 1 and 100 or (p_after is not null and p_after !~ '^[a-f0-9]{64}$') then
 raise exception 'Invalid list parameters' using errcode='22023'; end if;
 return query select e.id, e.received_at, char_length(e.content) from public.pit_entries e
 where p_after is null or e.id > p_after order by e.id limit p_limit;
end;
$$;
revoke all on function public.pit_saas_append(text) from public, anon;
revoke all on function public.pit_saas_list(text, integer) from public, anon;
grant execute on function public.pit_saas_append(text) to authenticated;
grant execute on function public.pit_saas_list(text, integer) to authenticated;
-- Hook changes only tokens for administrator-enabled Pit OAuth clients.
create function public.pit_access_token_hook(event jsonb) returns jsonb
language plpgsql stable security invoker set search_path = '' as $$
declare claims jsonb := event->'claims';
begin
 if exists (select 1 from public.pit_oauth_clients c where c.enabled and c.client_id = claims->>'client_id') then
  claims := jsonb_set(claims, '{aud}', '"https://pit.ohlabs.ai/mcp"'::jsonb);
  event := jsonb_set(event, '{claims}', claims);
 end if;
 return event;
end;
$$;
revoke all on function public.pit_access_token_hook(jsonb) from public, anon, authenticated;
grant usage on schema public to supabase_auth_admin;
grant select on public.pit_oauth_clients to supabase_auth_admin;
create policy pit_auth_hook_client_ids on public.pit_oauth_clients for select to supabase_auth_admin using (true);
grant execute on function public.pit_access_token_hook(jsonb) to supabase_auth_admin;
notify pgrst, 'reload schema';
commit;
