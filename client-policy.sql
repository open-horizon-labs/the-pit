begin;
create policy pit_client_read on public.entries for select to authenticated
  using ((select auth.uid()) = '9469508c-ba85-4b28-be01-1987b1d3d035'::uuid);
create policy pit_client_append on public.entries for insert to authenticated
  with check ((select auth.uid()) = '9469508c-ba85-4b28-be01-1987b1d3d035'::uuid);
commit;
