-- Proposed initial allowance: 1 GiB per account, adjustable by administrators.
-- Apply only after live inspection. Does not change personal public.entries.
begin;
create schema if not exists pit_private;
revoke all on schema pit_private from public, anon, authenticated;
create table pit_private.storage_allowances (
 user_id uuid primary key references auth.users(id) on delete cascade,
 used_bytes bigint not null default 0 check(used_bytes >= 0),
 max_bytes bigint not null default 1073741824 check(max_bytes >= 0)
);
alter table pit_private.storage_allowances enable row level security;
revoke all on pit_private.storage_allowances from public, anon, authenticated;
-- Block writes while backfilling accounting; no content is transformed.
lock table public.pit_entries in share row exclusive mode;
insert into pit_private.storage_allowances(user_id,used_bytes)
 select user_id,sum(octet_length(content)) from public.pit_entries group by user_id;
create function pit_private.account_storage() returns trigger
language plpgsql security definer set search_path = '' as $$
declare used bigint; allowance bigint; hash text;
begin
 if TG_OP = 'DELETE' then
  update pit_private.storage_allowances set used_bytes=used_bytes-octet_length(OLD.content) where user_id=OLD.user_id;
  return OLD;
 end if;
 insert into pit_private.storage_allowances(user_id) values(NEW.user_id) on conflict do nothing;
 select used_bytes,max_bytes into used,allowance from pit_private.storage_allowances where user_id=NEW.user_id for update;
 hash := encode(extensions.digest(NEW.content,'sha256'),'hex');
 -- After the account lock, another transaction's committed duplicate is visible.
 if exists(select 1 from public.pit_entries where user_id=NEW.user_id and id=hash) then return NEW; end if;
 if octet_length(NEW.content)::bigint > allowance-used then
  raise exception 'Pit storage allowance reached. No text was saved.' using errcode='P0001';
 end if;
 update pit_private.storage_allowances set used_bytes=used_bytes+octet_length(NEW.content) where user_id=NEW.user_id;
 return NEW;
end;
$$;
revoke all on function pit_private.account_storage() from public, anon, authenticated;
create trigger pit_storage_insert before insert on public.pit_entries for each row execute function pit_private.account_storage();
create trigger pit_storage_delete after delete on public.pit_entries for each row execute function pit_private.account_storage();
commit;
