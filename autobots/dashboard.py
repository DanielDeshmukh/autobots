"""Web dashboard for Autobots monitoring."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Simple HTTP server without external dependencies
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


@dataclass
class DashboardConfig:
    """Configuration for the web dashboard."""

    host: str = "127.0.0.1"
    port: int = 8080
    auto_open: bool = True


@dataclass
class DashboardData:
    """Data to display on the dashboard."""

    session_id: str = ""
    status: str = "idle"
    current_phase: str = ""
    phase_status: str = ""
    progress: float = 0.0
    total_phases: int = 0
    completed_phases: int = 0
    token_usage: dict[str, Any] = field(default_factory=dict)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_phase": self.current_phase,
            "phase_status": self.phase_status,
            "progress": self.progress,
            "total_phases": self.total_phases,
            "completed_phases": self.completed_phases,
            "token_usage": self.token_usage,
            "recent_events": self.recent_events,
            "config": self.config,
            "timestamp": time.time(),
        }


# HTML template for the dashboard
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autobots Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5rem;
            background: linear-gradient(135deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .header .subtitle {
            color: #888;
            margin-top: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #0f3460;
        }
        .card h2 {
            font-size: 1.2rem;
            color: #00d9ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card h2::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #0f3460;
        }
        .stat:last-child {
            border-bottom: none;
        }
        .stat .label {
            color: #888;
        }
        .stat .value {
            font-weight: 600;
            color: #fff;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #0f3460;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            border-radius: 10px;
            transition: width 0.3s ease;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-idle { background: #333; color: #888; }
        .status-running { background: #00d9ff33; color: #00d9ff; }
        .status-completed { background: #00ff8833; color: #00ff88; }
        .status-error { background: #ff444433; color: #ff4444; }
        .event-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .event-item {
            padding: 10px;
            margin-bottom: 8px;
            background: #0f3460;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        .event-item .time {
            color: #00d9ff;
            font-size: 0.8rem;
        }
        .event-item .message {
            margin-top: 5px;
        }
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #00d9ff, #00ff88);
            color: #1a1a2e;
            border: none;
            padding: 15px 25px;
            border-radius: 30px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0, 217, 255, 0.3);
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Autobots Dashboard</h1>
        <p class="subtitle">Real-time monitoring for your AI coding swarm</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Session Status</h2>
            <div class="stat">
                <span class="label">Status</span>
                <span class="status-badge status-idle" id="status">IDLE</span>
            </div>
            <div class="stat">
                <span class="label">Session ID</span>
                <span class="value" id="session-id">-</span>
            </div>
            <div class="stat">
                <span class="label">Current Phase</span>
                <span class="value" id="current-phase">-</span>
            </div>
        </div>

        <div class="card">
            <h2>Progress</h2>
            <div class="stat">
                <span class="label">Completed</span>
                <span class="value"><span id="completed">0</span> / <span id="total">0</span></span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
            </div>
            <div class="stat" style="margin-top: 15px;">
                <span class="label">Progress</span>
                <span class="value" id="progress-pct">0%</span>
            </div>
        </div>

        <div class="card">
            <h2>Token Usage</h2>
            <div class="stat">
                <span class="label">Input Tokens</span>
                <span class="value" id="input-tokens">0</span>
            </div>
            <div class="stat">
                <span class="label">Output Tokens</span>
                <span class="value" id="output-tokens">0</span>
            </div>
            <div class="stat">
                <span class="label">Estimated Cost</span>
                <span class="value" id="cost">$0.00</span>
            </div>
        </div>

        <div class="card">
            <h2>Recent Events</h2>
            <div class="event-list" id="events">
                <div class="empty-state">No events yet</div>
            </div>
        </div>
    </div>

    <button class="refresh-btn" onclick="refreshData()">Refresh</button>

    <script>
        async function refreshData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) {
                console.error('Failed to fetch data:', e);
            }
        }

        function updateDashboard(data) {
            // Status
            const statusEl = document.getElementById('status');
            statusEl.textContent = data.status.toUpperCase();
            statusEl.className = 'status-badge status-' + data.status;

            // Session
            document.getElementById('session-id').textContent = data.session_id || '-';
            document.getElementById('current-phase').textContent = data.current_phase || '-';

            // Progress
            document.getElementById('completed').textContent = data.completed_phases;
            document.getElementById('total').textContent = data.total_phases;
            document.getElementById('progress-pct').textContent = Math.round(data.progress * 100) + '%';
            document.getElementById('progress-fill').style.width = (data.progress * 100) + '%';

            // Token usage
            const usage = data.token_usage || {};
            document.getElementById('input-tokens').textContent = (usage.input || 0).toLocaleString();
            document.getElementById('output-tokens').textContent = (usage.output || 0).toLocaleString();
            document.getElementById('cost').textContent = '$' + (usage.cost || 0).toFixed(4);

            // Events
            const eventsEl = document.getElementById('events');
            const events = data.recent_events || [];
            if (events.length === 0) {
                eventsEl.innerHTML = '<div class="empty-state">No events yet</div>';
            } else {
                eventsEl.innerHTML = events.slice(-10).reverse().map(e => `
                    <div class="event-item">
                        <div class="time">${new Date(e.timestamp * 1000).toLocaleTimeString()}</div>
                        <div class="message">${e.message || e.type || 'Event'}</div>
                    </div>
                `).join('');
            }
        }

        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
        refreshData();
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    dashboard_data: DashboardData = DashboardData()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())

        elif parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(self.dashboard_data.to_dict()).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class WebDashboard:
    """Web dashboard for monitoring Autobots execution."""

    def __init__(self, config: DashboardConfig | None = None):
        self.config = config or DashboardConfig()
        self.data = DashboardData()
        self.server: HTTPServer | None = None
        self._running = False

    def update(self, **kwargs) -> None:
        """Update dashboard data."""
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)

    def add_event(self, event_type: str, message: str) -> None:
        """Add an event to the dashboard."""
        self.data.recent_events.append({
            "type": event_type,
            "message": message,
            "timestamp": time.time(),
        })
        # Keep only last 50 events
        self.data.recent_events = self.data.recent_events[-50:]

    def start(self) -> None:
        """Start the web server."""
        if self._running:
            return

        DashboardHandler.dashboard_data = self.data
        self.server = HTTPServer(
            (self.config.host, self.config.port),
            DashboardHandler,
        )
        self._running = True

        import threading
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

        if self.config.auto_open:
            import webbrowser
            webbrowser.open(f"http://{self.config.host}:{self.config.port}")

    def stop(self) -> None:
        """Stop the web server."""
        if self.server:
            self.server.shutdown()
            self._running = False

    @property
    def url(self) -> str:
        """Get the dashboard URL."""
        return f"http://{self.config.host}:{self.config.port}"


# Global dashboard instance
_dashboard: WebDashboard | None = None


def get_dashboard(config: DashboardConfig | None = None) -> WebDashboard:
    """Get or create the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = WebDashboard(config)
    return _dashboard
