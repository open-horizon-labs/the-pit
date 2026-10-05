-- Ranked literal retrieval over the personal corpus. Offsets count PostgreSQL
-- characters (Unicode code points), zero based, in the preserved source text.
begin;
create or replace function public.pit_query(
  p_terms text[], p_limit integer default 5, p_entry_ids text[] default null,
  p_since timestamptz default null, p_until timestamptz default null
)
returns jsonb language plpgsql stable security invoker set search_path = ''
as $function$
declare
  v_term text;
  v_result jsonb;
begin
  if p_terms is null or pg_catalog.cardinality(p_terms) not between 1 and 16
     or p_limit is null or p_limit not between 1 and 20
     or (p_entry_ids is not null and (pg_catalog.cardinality(p_entry_ids) > 100
       or exists (select 1 from pg_catalog.unnest(p_entry_ids) x where x is null or x !~ '^[a-f0-9]{64}$')))
     or (p_since is not null and p_until is not null and p_since >= p_until) then
    raise exception 'Invalid query parameters' using errcode = '22023';
  end if;
  foreach v_term in array p_terms loop
    if v_term is null or pg_catalog.char_length(v_term) not between 1 and 100
       or v_term ~ '^[[:space:]]*$' then
      raise exception 'Invalid query term' using errcode = '22023';
    end if;
  end loop;

  with terms as materialized (
    select distinct pg_catalog.lower(u.term) as term, '***=' || u.term as pattern
    from pg_catalog.unnest(p_terms) as u(term)
  ), candidates as materialized (
    select e.id, e.received_at, e.content,
      pg_catalog.char_length(e.content) as source_chars
    from public.entries e
    where (p_entry_ids is null or e.id = any(p_entry_ids))
      and (p_since is null or e.received_at >= p_since)
      and (p_until is null or e.received_at < p_until)
      and not exists (
        select 1 from terms t where not (e.content operator(pg_catalog.~*) t.pattern)
      )
    order by e.received_at desc, e.id
    limit 101
  ), bounded_candidates as materialized (
    select c.*, pg_catalog.substr(c.content, 1, 1000000) as bounded
    from candidates c
    order by c.received_at desc, c.id limit 100
  -- Prefix containment is exact text reuse within the already authorized scope.
  -- Keep a deterministic longer representative; never change captured entries.
  ), distinct_candidates as materialized (
    select c.* from bounded_candidates c
    where not exists (
      select 1 from bounded_candidates d
      where d.id <> c.id and pg_catalog.starts_with(d.bounded,c.bounded)
        and (least(d.source_chars,1000000) > least(c.source_chars,1000000)
          or (d.received_at,d.id) > (c.received_at,c.id))
    )
  ), windows as materialized (
    select c.id, c.received_at, c.source_chars, s.start_char,
      pg_catalog.substr(c.bounded, s.start_char + 1, 1800) as excerpt
    from distinct_candidates c
    cross join lateral pg_catalog.generate_series(0,
      greatest(0, pg_catalog.char_length(c.bounded) - 1), 1400) s(start_char)
  ), unique_windows as materialized (
    select distinct on (excerpt) * from windows order by excerpt, received_at desc, id, start_char
  ), scored as materialized (
    select w.id, w.received_at, w.source_chars, w.start_char,
      w.start_char + pg_catalog.char_length(w.excerpt) as end_char, w.excerpt,
      (select pg_catalog.count(distinct t.term)::integer from terms t
       where w.excerpt operator(pg_catalog.~*) t.pattern) as score,
      pg_catalog.ts_rank_cd(pg_catalog.to_tsvector('pg_catalog.simple',w.excerpt), pg_catalog.plainto_tsquery('pg_catalog.simple',pg_catalog.array_to_string(p_terms,' ')),32) as lexical_rank
    from unique_windows w
  ), matching as (
    select * from scored where score > 0
  ), ranked as (
    select * from matching
    order by score desc, lexical_rank desc, received_at desc, id, start_char
    limit p_limit
  )
  select pg_catalog.jsonb_build_object(
    'entries', coalesce((select pg_catalog.jsonb_agg(pg_catalog.jsonb_build_object(
      'id', r.id, 'received_at', r.received_at, 'start_char', r.start_char,
      'end_char', r.end_char, 'excerpt', r.excerpt, 'score', r.score, 'lexical_rank', r.lexical_rank
    ) order by r.score desc, r.lexical_rank desc, r.received_at desc, r.id, r.start_char) from ranked r), '[]'::jsonb),
    'coverage', pg_catalog.jsonb_build_object(
      'candidate_limit', 100, 'characters_per_entry', 1000000,
      'candidates_truncated', (select pg_catalog.count(*) > 100 from candidates),
      'characters_truncated', exists (select 1 from bounded_candidates where source_chars > 1000000)
    ),
    'offset_unit', 'unicode_code_points_zero_based'
  ) into v_result;
  return v_result;
end;
$function$;
revoke all on function public.pit_query(text[], integer, text[], timestamptz, timestamptz) from public, anon;
grant execute on function public.pit_query(text[], integer, text[], timestamptz, timestamptz) to authenticated;
notify pgrst, 'reload schema';
commit;
