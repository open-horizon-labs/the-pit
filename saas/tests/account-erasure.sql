begin;
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}',true);
select public.pit_saas_append('other account');
select set_config('request.jwt.claims','{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated","client_id":"trusted"}',true);
do $$ begin
 begin perform public.pit_erase_my_data(); raise exception 'OAuth deletion allowed';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims','{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}',true);
select public.pit_erase_my_data();
reset role;
do $$ begin
 if exists(select 1 from public.pit_entries where user_id='11111111-1111-1111-1111-111111111111') then raise exception 'own erasure failed'; end if;
 if not exists(select 1 from public.pit_entries where user_id='22222222-2222-2222-2222-222222222222') then raise exception 'cross-account erasure'; end if;
 if not exists(select 1 from auth.users where id='11111111-1111-1111-1111-111111111111') then raise exception 'shared identity deleted'; end if;
end $$;
rollback;
