import os
import shutil
import tempfile
import unittest
from download_ui import DownloadUI


class DummyResponse:
    def __init__(self, data: bytes, content_length=None):
        self.data = data
        self.headers = {}
        if content_length is not None:
            self.headers["content-length"] = str(content_length)

    def iter_content(self, chunk_size=1024):
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i : i + chunk_size]


class FailingResponse:
    def __init__(self, data: bytes):
        self.data = data
        self.headers = {"content-length": str(len(data) * 2)}

    def iter_content(self, chunk_size=1024):
        yield self.data[:100]
        raise ConnectionResetError("Connection lost mid-stream")


class TestDownloadUI(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ui = DownloadUI(no_color=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_successful_download(self):
        sample_data = b"X" * 5000
        resp = DummyResponse(sample_data, content_length=len(sample_data))
        dest = os.path.join(self.test_dir, "test.pdf")

        ok = self.ui.download_stream(resp, dest, "test.pdf")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(dest))
        self.assertFalse(os.path.exists(dest + ".part"))
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), sample_data)

    def test_failing_download_cleans_up_part_file(self):
        sample_data = b"X" * 5000
        resp = FailingResponse(sample_data)
        dest = os.path.join(self.test_dir, "fail.pdf")

        ok = self.ui.download_stream(resp, dest, "fail.pdf")
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(dest))
        self.assertFalse(os.path.exists(dest + ".part"))


if __name__ == "__main__":
    unittest.main()
