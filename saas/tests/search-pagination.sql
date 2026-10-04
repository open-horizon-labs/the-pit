-- Run only in a disposable local PostgreSQL initialized with bootstrap.sql and tenant-storage.sql.
begin;
insert into public.pit_entries (user_id, received_at, content) values
 ('11111111-1111-1111-1111-111111111111', '2030-01-03T00:00:00Z', 'pagination-probe newest'),
 ('11111111-1111-1111-1111-111111111111', '2030-01-02T00:00:00Z', 'pagination-probe tie-a'),
 ('11111111-1111-1111-1111-111111111111', '2030-01-02T00:00:00Z', 'pagination-probe tie-b'),
 ('11111111-1111-1111-1111-111111111111', '2030-01-01T00:00:00Z', 'pagination-probe older')
on conflict do nothing;
set local request.jwt.claims = '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}';
set local role authenticated;
create temporary table first_page as
 select * from public.pit_saas_search_page('pagination-probe', 2, 0, null, null);
create temporary table page_cursor as
 select received_at, id from first_page order by received_at desc, id offset 1 limit 1;
reset role;
-- Simulate an append that sorts ahead of the saved cursor.
insert into public.pit_entries (user_id, received_at, content)
values ('11111111-1111-1111-1111-111111111111', '2030-01-04T00:00:00Z', 'pagination-probe inserted-ahead')
on conflict do nothing;
set local role authenticated;
do $test$
declare
 first_ids text[];
 page_ids text[];
 tie_ids text[];
 cursor_time timestamptz;
 cursor_id text;
 newest_id text;
 ahead_id text;
 older_id text;
begin
 select array_agg(id order by id) into tie_ids from public.pit_entries
  where content in ('pagination-probe tie-a', 'pagination-probe tie-b');
 select id into newest_id from public.pit_entries where content = 'pagination-probe newest';
 select id into older_id from public.pit_entries where content = 'pagination-probe older';
 select array_agg(id order by received_at desc, id) into first_ids from first_page;
 if first_ids <> array[newest_id, tie_ids[1]] then raise exception 'First page order/tie break failed: %', first_ids; end if;
 select received_at, id into cursor_time, cursor_id from page_cursor;
 select id into ahead_id from public.pit_entries where content = 'pagination-probe inserted-ahead';
 select array_agg(id order by received_at desc, id) into page_ids
  from public.pit_saas_search_page('pagination-probe', 20, 0, cursor_time, cursor_id);
 if page_ids <> array[tie_ids[2], older_id] then raise exception 'Cursor page shifted or skipped a tied row: %', page_ids; end if;
 if ahead_id = any(page_ids) or ahead_id = any(first_ids) then raise exception 'New ahead row leaked into an existing traversal'; end if;

 begin
  perform * from public.pit_saas_search_page('pagination-probe', 2, 0, cursor_time, null);
  raise exception 'Unpaired cursor timestamp was accepted';
 exception when sqlstate '22023' then null;
 end;
 begin
  perform * from public.pit_saas_search_page('pagination-probe', 2, 0, null, cursor_id);
  raise exception 'Unpaired cursor ID was accepted';
 exception when sqlstate '22023' then null;
 end;
 begin
  perform * from public.pit_saas_search_page('pagination-probe', 21, 0, null, null);
  raise exception 'Oversized page limit was accepted';
 exception when sqlstate '22023' then null;
 end;
end;
$test$;
rollback;
