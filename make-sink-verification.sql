BEGIN;
SELECT rolcanlogin AS login_enabled, rolbypassrls AS bypass_rls,
  has_function_privilege('pit_make_sink','public.pit_append_text(text)','EXECUTE') AS can_append,
  has_table_privilege('pit_make_sink','public.entries','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS direct_table_access,
  has_any_column_privilege('pit_make_sink','public.entries','SELECT,INSERT,UPDATE,REFERENCES') AS direct_column_access
FROM pg_roles WHERE rolname='pit_make_sink';
DO $test$
DECLARE sample text := E'The Pit Make sink verification 2026-10-01\nUnicode: ž🙂\nQuotes: '' "\\\nPreserve trailing spaces  ';
BEGIN
  IF NOT public.pit_append_text(sample) THEN RAISE EXCEPTION 'First append did not insert'; END IF;
  IF public.pit_append_text(sample) THEN RAISE EXCEPTION 'Duplicate inserted'; END IF;
  IF (SELECT count(*) FROM public.entries WHERE content = sample) <> 1 THEN RAISE EXCEPTION 'Exact text mismatch'; END IF;
END;
$test$;
SELECT 'append, exact-text preservation and duplicate suppression passed; test writes rolled back' AS verification;
ROLLBACK;
