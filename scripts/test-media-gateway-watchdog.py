#!/usr/bin/env python3
"""Self-tests that never mount/unmount anything or connect to the Agent."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

script = Path(__file__).with_name("media-gateway-watchdog.py")
spec = importlib.util.spec_from_file_location("rm_media_watchdog", script)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.local = {
            "slug": "stormflix",
            "transport": "local",
            "backend_id": "stormflix-2",
            "source": Path("/mnt/rclone-manager-remotes/_media-pools/stormflix"),
            "dest": Path("/media-union/stormflix"),
        }

    def test_filter_rejects_unmanaged_paths(self):
        state = {"libraries": {
            "valid": {"backend_id": "x", "stable_path": "/media-union/stormflix"},
            "unsafe": {"backend_id": "x", "stable_path": "/mnt/user/Downloads"},
        }, "backends": {"x": {"transport": "local", "source_path": str(self.local["source"])}}}
        found = list(watch.library_entries(state))
        self.assertEqual([x["slug"] for x in found], ["valid"])

    def test_local_gateway_detects_matching_content(self):
        with patch.object(watch, "is_mount", return_value=True), patch.object(
            watch, "names", side_effect=[["Akumanimes"], ["Akumanimes", "Guilherme"]]
        ):
            self.assertEqual(watch.healthy(self.local)[0], True)

    def test_stale_gateway_detected_without_writing(self):
        with patch.object(watch, "is_mount", return_value=True), patch.object(
            watch, "names", side_effect=[[], ["Akumanimes", "Guilherme"]]
        ):
            self.assertEqual(watch.healthy(self.local)[0], False)

    def test_never_rebind_if_local_source_is_empty(self):
        with patch.object(watch, "is_mount", return_value=True), patch.object(
            watch, "names", side_effect=[[], []]
        ):
            self.assertIsNone(watch.healthy(self.local)[0])

    def test_remote_does_not_require_local_source(self):
        remote = dict(self.local, transport="sftp")
        with patch.object(watch, "is_mount", return_value=True), patch.object(
            watch, "names", return_value=[]
        ):
            self.assertTrue(watch.healthy(remote)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
