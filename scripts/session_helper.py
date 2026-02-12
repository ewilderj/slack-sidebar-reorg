"""Shared session management for slack-reorg scripts.

Session profiles are stored in ~/.slack-reorg/sessions/{workspace-hostname}/
e.g., ~/.slack-reorg/sessions/mycompany.slack.com/

This module provides:
- session_dir_for_workspace(): get/create the session directory
- ensure_playwright(): check Playwright + Chromium are installed
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path.home() / ".slack-reorg"
SESSIONS_DIR = DATA_DIR / "sessions"


def workspace_hostname(workspace_url):
    """Extract hostname from a workspace URL."""
    parsed = urlparse(workspace_url)
    host = parsed.hostname or parsed.path.strip("/")
    if not host:
        raise ValueError(f"Cannot extract hostname from: {workspace_url}")
    # Sanitize for filesystem
    return re.sub(r"[^a-zA-Z0-9._-]", "_", host)


def session_dir_for_workspace(workspace_url):
    """Return the session directory for a workspace, creating it if needed."""
    host = workspace_hostname(workspace_url)
    session_dir = SESSIONS_DIR / host
    session_dir.mkdir(parents=True, exist_ok=True)
    return str(session_dir)


def has_session(workspace_url):
    """Check if a session directory exists and has browser profile data."""
    host = workspace_hostname(workspace_url)
    session_dir = SESSIONS_DIR / host
    if not session_dir.exists():
        return False
    # Chromium profile creates several files/dirs on first launch
    contents = list(session_dir.iterdir())
    return len(contents) > 0


def ensure_playwright():
    """Check that Playwright and Chromium are available. Returns (ok, message)."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, (
            "Playwright is not installed.\n"
            "It should be installed automatically by uv via inline script metadata.\n"
            "Try: uv run --with playwright scripts/login"
        )

    return True, "Playwright is available."


def install_playwright_chromium():
    """Install Playwright's Chromium browser. Returns (ok, message)."""
    print("Installing Playwright Chromium browser...", file=sys.stderr)
    try:
        # Use uv if available, fall back to sys.executable
        uv_path = shutil.which("uv")
        if uv_path:
            cmd = [uv_path, "run", "--with", "playwright",
                   "-m", "playwright", "install", "chromium"]
        else:
            cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            return True, "Chromium installed successfully."
        else:
            return False, f"Chromium installation failed:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Chromium installation timed out."
    except Exception as e:
        return False, f"Error installing Chromium: {e}"
