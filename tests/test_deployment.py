"""Exercise stale deployments, soft 404s, missing assets, and catalogue drift."""

import json
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_catalogue import inspect
from check_site import Page, catalogue, validate_page
from verify_deployment import verify


@contextmanager
def fake_time():
    clock = [0]
    with patch("verify_deployment.time.monotonic", side_effect=lambda: clock[0]):
        with patch("verify_deployment.time.sleep", side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            yield


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.projects = catalogue()
        self.urls = "".join(f'<a href="{p["url"]}">{p["title"]}</a>' for p in self.projects)

    def response(self, url, revision, timeout):
        if "/revision.txt" in url:
            return b"current\n", "text/plain"
        if url.endswith("main.css"):
            return b"body {}", "text/css"
        titles = {"/": "Apps and tools", "/projects/": "What we've built", "/about/": "About Oddship"}
        route = url.removeprefix("https://example.test")
        return (titles[route] + self.urls + '<link rel="stylesheet" href="/main.css">').encode(), "text/html"

    @patch("verify_deployment.time.sleep")
    def test_stale_revision_is_retried_before_success(self, sleep):
        stale = True

        def fetch(url, revision, timeout):
            nonlocal stale
            if "/revision.txt" in url and stale:
                stale = False
                return b"old\n", "text/plain"
            return self.response(url, revision, timeout)

        with patch("verify_deployment.fetch", side_effect=fetch):
            verify("https://example.test", "current", timeout=1, interval=0)
        sleep.assert_called_once()

    def test_stale_revision_times_out(self):
        with fake_time(), patch("verify_deployment.fetch", return_value=(b"old", "text/plain")):
            with self.assertRaisesRegex(TimeoutError, "different revision"):
                verify("https://example.test", "current", timeout=1, interval=1)

    def test_soft_404_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing expected content"):
            validate_page("<h1>Not found</h1>", "/projects/", self.projects)

    def test_missing_project_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing project"):
            validate_page("<h1>Apps and tools</h1>", "/", self.projects)

    def test_minified_redirect_meta_is_parsed(self):
        page = Page('<meta http-equiv=refresh content="0;url=https://oddship.net/projects/">')
        self.assertEqual(page.redirects, ["0;url=https://oddship.net/projects/"])

    def test_html_instead_of_css_is_rejected(self):
        def fetch(url, revision, timeout):
            if url.endswith("main.css"):
                return b"<h1>Not found</h1>", "text/html"
            return self.response(url, revision, timeout)

        with fake_time(), patch("verify_deployment.fetch", side_effect=fetch):
            with self.assertRaisesRegex(TimeoutError, "invalid public asset"):
                verify("https://example.test", "current", timeout=1, interval=1)

    def test_catalogue_requires_action_and_alt_text(self):
        for key, value, message in [("action", "", "homepage action"), ("image_alt", "", "image description")]:
            project = next(p.copy() for p in self.projects if p.get("homepage") and p.get("image"))
            project[key] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "projects.json"
                path.write_text(json.dumps([project]))
                with self.assertRaisesRegex(ValueError, message):
                    catalogue(path)

    def test_catalogue_drift_reports_missing_archived_and_new_projects(self):
        projects = [{"name": "missing"}, {"name": "archived"}]
        repos = [{"name": "archived", "archived": True}, {"name": "new", "archived": False}]
        issues, candidates = inspect(projects, repos)
        self.assertEqual(len(issues), 2)
        self.assertEqual([p["name"] for p in candidates], ["new"])


if __name__ == "__main__":
    unittest.main()
