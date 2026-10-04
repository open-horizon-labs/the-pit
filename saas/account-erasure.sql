-- Prepared lifecycle operation. Inspect live schema before applying.
-- Erases only this user's SaaS Pit; never deletes shared Intake Auth or personal entries.
begin;
create function public.pit_erase_my_data() returns bigint
language plpgsql security definer set search_path = '' as $$
declare owner uuid := auth.uid(); removed bigint;
begin
 if owner is null or (auth.jwt()->>'role') is distinct from 'authenticated' or auth.jwt()->>'client_id' is not null then
  raise exception 'Account sign-in required; OAuth tools cannot erase data.' using errcode='42501';
 end if;
 -- Coordinate with the quota trigger if the allowance migration is present.
 if to_regclass('pit_private.storage_allowances') is not null then
  execute 'select user_id from pit_private.storage_allowances where user_id=$1 for update' using owner;
 end if;
 delete from public.pit_entries where user_id=owner;
 get diagnostics removed = row_count;
 return removed;
end;
$$;
revoke all on function public.pit_erase_my_data() from public, anon;
grant execute on function public.pit_erase_my_data() to authenticated;
notify pgrst,'reload schema';
commit;
