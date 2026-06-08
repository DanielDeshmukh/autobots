"""Tests for web dashboard."""

import json
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from autobots.dashboard import (
    DASHBOARD_HTML,
    DashboardConfig,
    DashboardData,
    WebDashboard,
    get_dashboard,
)


class TestDashboardConfig(unittest.TestCase):
    """Tests for DashboardConfig dataclass."""

    def test_default_config(self):
        config = DashboardConfig()
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8080)
        self.assertTrue(config.auto_open)

    def test_custom_config(self):
        config = DashboardConfig(host="0.0.0.0", port=9090, auto_open=False)
        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9090)
        self.assertFalse(config.auto_open)


class TestDashboardData(unittest.TestCase):
    """Tests for DashboardData dataclass."""

    def test_default_data(self):
        data = DashboardData()
        self.assertEqual(data.status, "idle")
        self.assertEqual(data.progress, 0.0)

    def test_to_dict(self):
        data = DashboardData(
            session_id="test-session",
            status="running",
            current_phase="P1",
        )
        d = data.to_dict()
        self.assertEqual(d["session_id"], "test-session")
        self.assertEqual(d["status"], "running")
        self.assertIn("timestamp", d)

    def test_add_events(self):
        data = DashboardData()
        data.recent_events.append({"type": "test", "message": "Test event"})
        self.assertEqual(len(data.recent_events), 1)


class TestWebDashboard(unittest.TestCase):
    """Tests for WebDashboard class."""

    def test_dashboard_creation(self):
        dashboard = WebDashboard()
        self.assertIsNotNone(dashboard.data)
        self.assertEqual(dashboard.data.status, "idle")

    def test_update_data(self):
        dashboard = WebDashboard()
        dashboard.update(status="running", current_phase="P1")
        self.assertEqual(dashboard.data.status, "running")
        self.assertEqual(dashboard.data.current_phase, "P1")

    def test_add_event(self):
        dashboard = WebDashboard()
        dashboard.add_event("phase_started", "Phase P1 started")
        self.assertEqual(len(dashboard.data.recent_events), 1)
        self.assertEqual(dashboard.data.recent_events[0]["type"], "phase_started")

    def test_url_property(self):
        config = DashboardConfig(host="localhost", port=9999)
        dashboard = WebDashboard(config)
        self.assertEqual(dashboard.url, "http://localhost:9999")

    def test_singleton_dashboard(self):
        d1 = get_dashboard()
        d2 = get_dashboard()
        self.assertIs(d1, d2)


class TestDashboardHTML(unittest.TestCase):
    """Tests for dashboard HTML."""

    def test_html_not_empty(self):
        self.assertGreater(len(DASHBOARD_HTML), 100)

    def test_html_contains_elements(self):
        self.assertIn("<html", DASHBOARD_HTML)
        self.assertIn("Autobots Dashboard", DASHBOARD_HTML)
        self.assertIn("/api/data", DASHBOARD_HTML)


class TestDashboardServer(unittest.TestCase):
    """Tests for the dashboard server (integration tests)."""

    def test_server_start_stop(self):
        config = DashboardConfig(port=18765, auto_open=False)
        dashboard = WebDashboard(config)

        dashboard.start()
        time.sleep(0.5)  # Give server time to start

        # Server should be running
        self.assertTrue(dashboard._running)

        dashboard.stop()
        time.sleep(0.5)

    def test_server_responds(self):
        config = DashboardConfig(port=18766, auto_open=False)
        dashboard = WebDashboard(config)

        dashboard.start()
        time.sleep(0.5)

        try:
            # Test HTML endpoint
            response = urllib.request.urlopen(f"http://127.0.0.1:18766/")
            self.assertEqual(response.status, 200)
            content = response.read().decode()
            self.assertIn("Autobots Dashboard", content)

            # Test API endpoint
            response = urllib.request.urlopen(f"http://127.0.0.1:18766/api/data")
            self.assertEqual(response.status, 200)
            data = json.loads(response.read())
            self.assertIn("status", data)
        finally:
            dashboard.stop()

    def test_api_returns_data(self):
        config = DashboardConfig(port=18767, auto_open=False)
        dashboard = WebDashboard(config)
        dashboard.update(status="running", current_phase="P1")

        dashboard.start()
        time.sleep(0.5)

        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:18767/api/data")
            data = json.loads(response.read())
            self.assertEqual(data["status"], "running")
            self.assertEqual(data["current_phase"], "P1")
        finally:
            dashboard.stop()


if __name__ == "__main__":
    unittest.main()
