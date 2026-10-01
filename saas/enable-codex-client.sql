begin;
insert into public.pit_oauth_clients(client_id,enabled) values ('24ac42eb-bd23-4fae-8eb1-540e4cefe213',true);
commit;
select client_id, enabled from public.pit_oauth_clients;
