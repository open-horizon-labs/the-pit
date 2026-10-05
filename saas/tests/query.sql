-- Run in disposable PostgreSQL after bootstrap.sql, tenant-storage.sql,
-- query.sql and saas/query.sql. Fixtures and role changes roll back.
begin;
create table if not exists public.entries (
  id text generated always as (encode(extensions.digest(content, 'sha256'), 'hex')) stored,
  received_at timestamptz not null, content text not null, primary key(id)
);
grant select on public.entries to authenticated;
insert into public.pit_entries(user_id, received_at, content) values
 ('11111111-1111-1111-1111-111111111111','2030-01-01T00:00:00Z','unicode marker: 🧭 café needle'),
 ('11111111-1111-1111-1111-111111111111','2030-01-02T00:00:00Z',repeat('a',3000) || ' late needle'),
 ('11111111-1111-1111-1111-111111111111','2030-01-03T00:00:00Z',repeat('d',1800) || ' suffix-a'),
 ('11111111-1111-1111-1111-111111111111','2030-01-04T00:00:00Z',repeat('d',1800) || ' suffix-b'),
 ('22222222-2222-2222-2222-222222222222','2030-01-05T00:00:00Z','other tenant marker othersecret needle'),
 ('11111111-1111-1111-1111-111111111111','2030-01-06T00:00:00Z','literal x.*'' OR true-- value'),
 ('11111111-1111-1111-1111-111111111111','2030-01-07T00:00:00Z','alpha ' || repeat('🧭',3000) || ' alpha beta');
insert into public.pit_entries(user_id, received_at, content)
select '11111111-1111-1111-1111-111111111111', '2030-02-01T00:00:00Z'::timestamptz + n * interval '1 second',
  'candidate flood needle #' || n from generate_series(1,101) n;
insert into public.pit_entries(user_id, received_at, content)
values ('11111111-1111-1111-1111-111111111111','2030-03-01T00:00:00Z',
  'longneedle' || repeat('z',1000001) || ' hiddenpastcap');
insert into public.pit_entries(user_id,received_at,content) values
 ('11111111-1111-1111-1111-111111111111','2030-01-01','prefixprobe alpha beta'),
 ('11111111-1111-1111-1111-111111111111','2030-01-02','prefixprobe alpha beta extra');
insert into public.entries(received_at,content) values
 ('2030-01-01T00:00:00Z','unicode marker: 🧭 café needle'),
 ('2030-01-02T00:00:00Z',repeat('a',3000) || ' late needle'),
 ('2030-01-03T00:00:00Z',repeat('d',1800) || ' suffix-a'),
 ('2030-01-04T00:00:00Z',repeat('d',1800) || ' suffix-b'),
 ('2030-01-06T00:00:00Z','literal x.*'' OR true-- value'),
 ('2030-01-07T00:00:00Z','alpha ' || repeat('🧭',3000) || ' alpha beta');

set local request.jwt.claims = '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}';
set local role authenticated;
do $test$
declare
  r jsonb;
  e jsonb;
  expected_id text;
  late_id text;
  other_id text;
  c integer;
begin
  select id into expected_id from public.pit_entries where content='unicode marker: 🧭 café needle' and user_id=auth.uid();
  r := public.pit_saas_query(array['🧭','NEEDLE'], 20,array[expected_id]);
  if not r->'coverage' @> '{"candidate_limit":100,"characters_per_entry":1000000,"candidates_truncated":false,"characters_truncated":false}'::jsonb then
    raise exception 'Unexpected ordinary coverage: %', r->'coverage'; end if;
  select value into e from jsonb_array_elements(r->'entries') where value->>'id'=expected_id;
  if e is null or e->>'start_char' <> '0' or e->>'excerpt' <> 'unicode marker: 🧭 café needle'
     or r->>'offset_unit' <> 'unicode_code_points_zero_based' then
    raise exception 'Unicode original-slice/offset check failed: %', r; end if;

  select id into late_id from public.pit_entries where content like '%late needle%' and user_id=auth.uid();
  r := public.pit_saas_query(array['needle'],20,array[late_id]);
  select value into e from jsonb_array_elements(r->'entries') where value->>'excerpt' like '%late needle%' and value->>'start_char'='1400';
  if e is null or e->>'start_char' <> '1400' or e->>'end_char' <> '3012' then
    raise exception 'Late overlapping-window match failed: %', e; end if;

  r := public.pit_saas_query(array['d'],20,array(select id from public.pit_entries where user_id=auth.uid() and content like repeat('d',1800) || ' suffix-%'));
  select count(*) into c from jsonb_array_elements(r->'entries') where value->>'excerpt' = repeat('d',1800);
  if c <> 1 then raise exception 'Exact excerpt dedup failed: % occurrences', c; end if;

  select id into expected_id from public.pit_entries where content like '%literal x.%' and user_id=auth.uid();
  r := public.pit_saas_query(array['x.*'' OR true--'],20,array[expected_id]);
  if jsonb_array_length(r->'entries') <> 1 or r->'entries'->0->>'id' <> expected_id then
    raise exception 'Literal/malicious term or ID scope failed: %', r; end if;

  r := public.pit_saas_query(array['needle'],20,null,'2030-01-02T00:00:00Z','2030-01-03T00:00:00Z');
  if jsonb_array_length(r->'entries') <> 2 or exists(select 1 from jsonb_array_elements(r->'entries') x
      where x->>'id' <> late_id) then
    raise exception 'Receipt-time bounds failed: %', r; end if;

  r := public.pit_saas_query(array['needle'],1);
  if r->'coverage'->>'candidates_truncated' <> 'true' then raise exception '101st probe did not mark candidate truncation'; end if;
  r := public.pit_saas_query(array['longneedle'],20);
  if r->'coverage'->>'characters_truncated' <> 'true' then raise exception 'Long source did not mark character truncation'; end if;

  r := public.pit_saas_query(array['hiddenpastcap']);
  if jsonb_array_length(r->'entries') <> 0 or r->'coverage'->>'characters_truncated' <> 'true' then
    raise exception 'Empty result beyond scan cap lost incomplete coverage'; end if;
  expected_id := encode(extensions.digest('prefixprobe alpha beta','sha256'),'hex');
  r := public.pit_saas_query(array['prefixprobe']);
  if jsonb_array_length(r->'entries') <> 1 or r->'entries'->0->>'excerpt' <> 'prefixprobe alpha beta extra' then
    raise exception 'Exact prefix reuse failed'; end if;
  r := public.pit_saas_query(array['prefixprobe'],5,array[expected_id]);
  if jsonb_array_length(r->'entries') <> 1 or r->'entries'->0->>'id' <> expected_id then
    raise exception 'Prefix reuse widened the authorized entry scope'; end if;

  other_id := encode(extensions.digest('other tenant marker othersecret needle','sha256'),'hex');
  r := public.pit_saas_query(array['othersecret'],20,array[other_id]);
  if jsonb_array_length(r->'entries') <> 0 then raise exception 'RLS leaked another tenant through ID filter: %', r; end if;
  r := public.pit_saas_query(array['othersecret'],20);
  if exists(select 1 from jsonb_array_elements(r->'entries') x where x->>'id'=other_id) then
    raise exception 'RLS leaked another tenant through broad search'; end if;

  r := public.pit_query(array['🧭','NEEDLE'],20);
  if jsonb_array_length(r->'entries') <> 1 or r->'entries'->0->>'excerpt' <> 'unicode marker: 🧭 café needle'
     or r->'entries'->0->>'start_char' <> '0' then
    raise exception 'Personal query parity/Unicode test failed: %', r; end if;
  r := public.pit_query(array['x.*'' OR true--'],20);
  if jsonb_array_length(r->'entries') <> 1 then raise exception 'Personal literal search failed: %', r; end if;

  r := public.pit_saas_query(array['alpha','beta'],1);
  if r->'entries'->0->>'score' <> '2' or (r->'entries'->0->>'start_char')::integer = 0 then
    raise exception 'Early partial match outranked later complete evidence'; end if;
  for e in select value from jsonb_array_elements(r->'entries') loop
    if not exists(select 1 from public.pit_entries t where t.id=e->>'id'
      and substr(t.content,(e->>'start_char')::integer+1,
        (e->>'end_char')::integer-(e->>'start_char')::integer)=e->>'excerpt') then
      raise exception 'Original non-BMP range does not round trip'; end if;
  end loop;
  r := public.pit_saas_query(array['needle'],5,array[]::text[]);
  if jsonb_array_length(r->'entries') <> 0 then raise exception 'Empty ID scope widened'; end if;
  r := public.pit_saas_query(array['needle','NEEDLE'],5,array[late_id]);
  if (r->'entries'->0->>'score')::integer <> 1 then raise exception 'Repeated term inflated score'; end if;
  begin perform public.pit_saas_query(array['needle'],5,null,'2030-01-01','2030-01-01'); raise exception 'Equal bounds accepted';
  exception when sqlstate '22023' then null; end;

  begin perform public.pit_saas_query(array[' '],5); raise exception 'Blank term accepted';
  exception when sqlstate '22023' then null; end;
  begin perform public.pit_saas_query(array['needle'],21); raise exception 'Oversized result limit accepted';
  exception when sqlstate '22023' then null; end;
  begin perform public.pit_saas_query(array['needle'],5,array[repeat('a',64)],'2030-02-01','2030-01-01'); raise exception 'Reversed receipt bounds accepted';
  exception when sqlstate '22023' then null; end;
end;
$test$;
-- A second real role-scoped call must see its own fixture, while the first
-- account's otherwise matching text stays absent.
set local request.jwt.claims = '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}';
do $test$
declare r jsonb;
begin
 r := public.pit_saas_query(array['othersecret']);
 if jsonb_array_length(r->'entries') <> 1 then raise exception 'Second tenant cannot read own evidence'; end if;
 r := public.pit_saas_query(array['alpha']);
 if jsonb_array_length(r->'entries') <> 0 then raise exception 'First tenant leaked to second'; end if;
end;
$test$;
reset role;
set local role anon;
do $test$
begin
 begin perform public.pit_saas_query(array['needle']); raise exception 'Anonymous query accepted';
 exception when insufficient_privilege then null; end;
end;
$test$;
rollback;
