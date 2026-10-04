begin;
insert into public.pit_oauth_clients(client_id,enabled) values ('79c0b4f7-d42d-47f2-9a65-2cfb38f16ab4',true);
commit;
select client_id, enabled from public.pit_oauth_clients;
