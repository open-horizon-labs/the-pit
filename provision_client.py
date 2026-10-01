"""One-time trusted bootstrap using the already signed-in Supabase CLI.

Admin keys stay in memory. Only the restricted Auth session is saved locally.
"""

import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

SCRIPTS = Path(__file__).parent / "plugin/skills/export-to-pit/scripts"
sys.path.insert(0, str(SCRIPTS))
from pit_client import CONFIG, PitError, request, save_config

REF = "iunbpyiylsbkscjaisid"
URL = f"https://{REF}.supabase.co"
PENDING = CONFIG.parent / "provisioning.json"


def main():
    if CONFIG.exists():
        print("Client session already configured; existing credentials left unchanged.")
        return
    result = subprocess.run(["supabase", "projects", "api-keys", "--project-ref", REF,
                             "--output", "json"], capture_output=True, text=True)
    if result.returncode:
        raise PitError("Authenticated CLI key lookup failed; no keys displayed")
    keys = json.loads(result.stdout)
    admin = next(x["api_key"] for x in keys if x.get("name") == "service_role")
    public = next(x["api_key"] for x in keys if x.get("type") == "publishable")
    if PENDING.exists():
        pending = json.loads(PENDING.read_text())
        if not pending.get("user_id"):
            raise PitError("Previous user creation has an unresolved outcome; recover it before retrying")
    else:
        pending = {"email": f"pit-client-{uuid.uuid4()}@example.invalid",
                   "password": secrets.token_urlsafe(48)}
        save_config(pending, PENDING)
        user = request(URL + "/auth/v1/admin/users", admin, "POST",
                       {**pending, "email_confirm": True,
                        "app_metadata": {"pit_client": True}}, admin)
        pending["user_id"] = user["id"]
        save_config(pending, PENDING)
    session = request(URL + "/auth/v1/token?grant_type=password", public, "POST",
                      {"email": pending["email"], "password": pending["password"]})
    if session["user"]["id"] != pending["user_id"]:
        raise PitError("Unexpected sign-in identity")
    save_config({"url": URL, "publishable_key": public,
                 "user_id": session["user"]["id"], "access_token": session["access_token"],
                 "refresh_token": session["refresh_token"],
                 "expires_at": time.time() + session["expires_in"]})
    PENDING.unlink()
    identity = str(uuid.UUID(session["user"]["id"]))
    sql = f"""begin;
create policy pit_client_read on public.entries for select to authenticated
  using ((select auth.uid()) = '{identity}'::uuid);
create policy pit_client_append on public.entries for insert to authenticated
  with check ((select auth.uid()) = '{identity}'::uuid);
commit;
"""
    (Path(__file__).parent / "client-policy.sql").write_text(sql)
    print(json.dumps({"configured": True, "user_id": identity,
                      "session_file": str(CONFIG), "admin_key_saved": False,
                      "password_saved": False, "policy_applied": False}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (PitError, OSError, ValueError, KeyError, StopIteration):
        print("Provisioning did not finish. Inspect non-secret state before retrying; credentials not displayed.",
              file=sys.stderr)
        sys.exit(1)
