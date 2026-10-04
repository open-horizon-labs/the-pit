-- Disposable local PostgreSQL after tenant-storage.sql and storage-allowance.sql.
begin;
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}',true);
select public.pit_saas_append('🙂é');
select public.pit_saas_append('🙂é');
reset role;
do $$ begin
 if (select used_bytes from pit_private.storage_allowances where user_id='11111111-1111-1111-1111-111111111111') <> 6 then raise exception 'UTF8 accounting or dedup failed'; end if;
end $$;
update pit_private.storage_allowances set max_bytes=6 where user_id='11111111-1111-1111-1111-111111111111';
set local role authenticated;
select public.pit_saas_append('🙂é');
do $$ begin
 begin insert into public.pit_entries(content) values('x'); raise exception 'quota bypass';
 exception when sqlstate 'P0001' then if SQLERRM <> 'Pit storage allowance reached. No text was saved.' then raise; end if; end;
end $$;
reset role;
do $$ begin
 if (select used_bytes from pit_private.storage_allowances where user_id='11111111-1111-1111-1111-111111111111') <> 6 then raise exception 'failed write changed accounting'; end if;
end $$;
delete from public.pit_entries where user_id='11111111-1111-1111-1111-111111111111';
do $$ begin
 if (select used_bytes from pit_private.storage_allowances where user_id='11111111-1111-1111-1111-111111111111') <> 0 then raise exception 'erasure accounting'; end if;
end $$;
rollback;
