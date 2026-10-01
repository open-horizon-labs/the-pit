-- Dedicated Make sink: accepts exact text, ignores exact repeats.
-- Apply as postgres. Credential activation is a separate user step.
BEGIN;
CREATE ROLE pit_make_sink NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT ON DATABASE postgres TO pit_make_sink;
GRANT USAGE ON SCHEMA public TO pit_make_sink;
CREATE FUNCTION public.pit_append_text(content text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
BEGIN
  INSERT INTO public.entries(content) VALUES (pit_append_text.content)
  ON CONFLICT (id) DO NOTHING;
  RETURN FOUND;
END;
$function$;
REVOKE ALL ON FUNCTION public.pit_append_text(text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.pit_append_text(text) TO pit_make_sink;
COMMENT ON FUNCTION public.pit_append_text(text) IS 'Append exact text to The Pit. Returns true when new text was inserted; false for an exact repeat.';
NOTIFY pgrst, 'reload schema';
COMMIT;
