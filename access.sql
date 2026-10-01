-- Initial table-only hardening. Policies are added for the provisioned client UID.
begin;
alter table public.entries enable row level security;
revoke all privileges on table public.entries from anon, authenticated;
revoke insert (id, received_at, content), update (id, received_at, content),
  references (id, received_at, content), select (id, received_at, content)
  on public.entries from anon, authenticated;
grant select (id, received_at, content), insert (content)
  on public.entries to authenticated;
commit;
