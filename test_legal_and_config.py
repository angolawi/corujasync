import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.events import DownloadObserver, ProgressEvent, StatusEvent, DisciplineEvent
from core.config import load_config, save_config, DEFAULT_CONFIG
from legal.license_verifier import is_eula_accepted, accept_eula
from legal.eula_text import EULA_FULL_TEXT, EULA_TITLE


class MockObserver(DownloadObserver):
    def __init__(self):
        self.progress_events = []
        self.status_events = []
        self.discipline_events = []

    def on_progress(self, event: ProgressEvent) -> None:
        self.progress_events.append(event)

    def on_status(self, event: StatusEvent) -> None:
        self.status_events.append(event)

    def on_discipline(self, event: DisciplineEvent) -> None:
        self.discipline_events.append(event)


class TestLegalAndConfig(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_patch = patch("core.config.CONFIG_FILE_PATH", os.path.join(self.test_dir, "config.json"))
        self.app_dir_patch = patch("core.config.get_app_dir", return_value=self.test_dir)
        self.config_patch.start()
        self.app_dir_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.app_dir_patch.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_config_loading(self):
        cfg = load_config()
        self.assertFalse(cfg["eula_accepted"])
        self.assertEqual(cfg["preferred_quality"], "720p")

    def test_save_and_reload_config(self):
        cfg = load_config()
        cfg["download_videos"] = True
        cfg["preferred_quality"] = "480p"
        save_config(cfg)

        reloaded = load_config()
        self.assertTrue(reloaded["download_videos"])
        self.assertEqual(reloaded["preferred_quality"], "480p")

    def test_eula_acceptance(self):
        self.assertFalse(is_eula_accepted())
        accept_eula()
        self.assertTrue(is_eula_accepted())

        cfg = load_config()
        self.assertTrue(cfg["eula_accepted"])
        self.assertIsNotNone(cfg["eula_accepted_at"])

    def test_observer_events(self):
        observer = MockObserver()
        p_event = ProgressEvent(
            filename="teste.pdf",
            downloaded_bytes=100,
            total_bytes=200,
            speed_bytes_sec=1024.0,
            eta_seconds=1.0,
            percent=50.0,
        )
        observer.on_progress(p_event)
        self.assertEqual(len(observer.progress_events), 1)
        self.assertEqual(observer.progress_events[0].percent, 50.0)
        self.assertAlmostEqual(observer.progress_events[0].speed_mbps, 1024.0 / (1024 * 1024))
        self.assertAlmostEqual(observer.progress_events[0].ratio, 0.5)

        # Testa evento sem total_bytes
        p_event_no_total = ProgressEvent(
            filename="teste2.pdf",
            downloaded_bytes=500,
            total_bytes=None,
            speed_bytes_sec=2048.0,
            eta_seconds=None,
            percent=25.0,
        )
        self.assertAlmostEqual(p_event_no_total.ratio, 0.25)
        self.assertAlmostEqual(p_event_no_total.speed_mbps, 2048.0 / (1024 * 1024))

        s_event = StatusEvent(level="info", message="Teste")
        observer.on_status(s_event)
        self.assertEqual(len(observer.status_events), 1)


if __name__ == "__main__":
    unittest.main()
