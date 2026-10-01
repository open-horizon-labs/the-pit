import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/export-to-pit/scripts/pit_client.py"
spec = importlib.util.spec_from_file_location("pit_client", SCRIPT)
client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client_module)


class ClientTests(unittest.TestCase):
    def test_readers_use_only_rpc_and_keep_literal_query(self):
        with patch.object(self.client, "api", return_value=[]) as api:
            self.client.search("C++%_")
            api.assert_called_once_with("rpc/pit_search", "POST", {"p_query": "C++%_", "p_limit": 5, "p_context": 500})
            api.reset_mock()
            self.client.read_range("a" * 64, 3, 8)
            api.assert_called_once_with("rpc/pit_read_range", "POST", {"p_id": "a" * 64, "p_start": 3, "p_end": 8})

    def test_invalid_reader_bounds_never_reach_server(self):
        with patch.object(self.client, "api") as api:
            for args in [("",), ("x", 21), ("x", 5, -1)]:
                with self.assertRaises(client_module.PitError):
                    self.client.search(*args)
            for bounds in [(-1, 2), (3, 2), (0, 20001), (2147483648, 2147483648)]:
                with self.assertRaises(client_module.PitError):
                    self.client.read_range("a" * 64, *bounds)
            api.assert_not_called()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "private/connection.json"
        self.config = {"url": "https://test.supabase.co", "publishable_key": "public-test",
                       "user_id": "user-test", "access_token": "access-test",
                       "refresh_token": "refresh-test", "expires_at": time.time() + 600}
        client_module.save_config(self.config, self.path)
        self.client = client_module.Client(self.path)
        self.addCleanup(self.folder.cleanup)

    def test_append_sends_only_exact_content_and_checks_readback(self):
        text = "  héllo\r\nworld  "
        identity = hashlib.sha256(text.encode()).hexdigest()
        responses = [[{"id": identity}], [{"id": identity, "received_at": "first", "content": text}]]
        with patch.object(client_module, "request", side_effect=responses) as send:
            receipt = self.client.append(text)
        self.assertTrue(receipt["inserted"])
        args = send.call_args_list[0].args
        self.assertEqual(args[3], {"content": text})
        self.assertIn("resolution=ignore-duplicates", args[5])
        self.assertEqual(receipt["id"], identity)

    def test_duplicate_preserves_first_receipt(self):
        text = "same"
        identity = hashlib.sha256(text.encode()).hexdigest()
        with patch.object(client_module, "request", side_effect=[[], [{"id": identity, "received_at": "first", "content": text}]]):
            receipt = self.client.append(text)
        self.assertFalse(receipt["inserted"])
        self.assertEqual(receipt["received_at"], "first")

    def test_failed_readback_is_unknown_and_does_not_retry_append(self):
        with patch.object(client_module, "request", side_effect=[[{}], client_module.PitError("denied")]) as send:
            with self.assertRaises(client_module.DeliveryUnknown):
                self.client.append("saved maybe")
        self.assertEqual(send.call_count, 2)

    def test_recovery_compares_privately_without_returning_content(self):
        text = "private transcript\r\n  "
        identity = hashlib.sha256(text.encode()).hexdigest()
        with patch.object(self.client, "read", return_value={"id": identity, "received_at": "first", "content": text}):
            result = self.client.verify(text)
        self.assertEqual(result, {"id": identity, "received_at": "first", "found": True, "verified": True})
        self.assertNotIn(text, json.dumps(result))
        with patch.object(self.client, "read", return_value=None):
            self.assertFalse(self.client.verify(text)["found"])
        with patch.object(self.client, "read", return_value={"content": "different"}):
            with self.assertRaises(client_module.PitError):
                self.client.verify(text)

    def test_refresh_persists_rotated_token_and_preserves_private_permissions(self):
        self.config["expires_at"] = 0
        client_module.save_config(self.config, self.path)
        session = {"user": {"id": "user-test"}, "access_token": "new-access",
                   "refresh_token": "new-refresh", "expires_in": 3600}
        with patch.object(client_module, "request", return_value=session) as send:
            self.client.ensure_session()
            self.client.ensure_session()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(json.loads(self.path.read_text())["refresh_token"], "new-refresh")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)

    def test_refuses_wrong_refresh_identity_without_persisting_it(self):
        self.config["expires_at"] = 0
        client_module.save_config(self.config, self.path)
        with patch.object(client_module, "request", return_value={"user": {"id": "other"}}):
            with self.assertRaises(client_module.PitError):
                self.client.ensure_session()
        self.assertEqual(json.loads(self.path.read_text())["user_id"], "user-test")

    def test_refuses_untrusted_endpoint_or_world_readable_credentials(self):
        self.path.chmod(0o644)
        with self.assertRaises(client_module.PitError):
            client_module.Client(self.path)
        self.config["url"] = "https://unrelated.example"
        client_module.save_config(self.config, self.path)
        with self.assertRaises(client_module.PitError):
            client_module.Client(self.path)


if __name__ == "__main__":
    unittest.main()
