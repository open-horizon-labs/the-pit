-- Add generic keyset search without changing existing search RPC callers.
begin;
create or replace function public.pit_saas_search_page(
  p_query text, p_limit integer default 5, p_context integer default 500,
  p_before_received_at timestamptz default null, p_before_id text default null
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
     or p_context is null or p_context not between 0 and 2000
     or (p_before_received_at is null) <> (p_before_id is null)
     or (p_before_id is not null and p_before_id !~ '^[a-f0-9]{64}$') then
    raise exception 'Invalid search page parameters' using errcode = '22023';
  end if;
  v_pattern := '***=' || p_query;
  return query
  with candidates as materialized (
    select e.id, e.received_at, e.content
    from public.pit_entries e
    where e.content operator(pg_catalog.~*) v_pattern
      and (p_before_received_at is null
        or e.received_at < p_before_received_at
        or (e.received_at = p_before_received_at and e.id > p_before_id))
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
revoke all on function public.pit_saas_search_page(text, integer, integer, timestamptz, text) from public, anon;
grant execute on function public.pit_saas_search_page(text, integer, integer, timestamptz, text) to authenticated;
notify pgrst, 'reload schema';
commit;
