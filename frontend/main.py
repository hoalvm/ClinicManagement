"""Desktop application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.core.config import get_frontend_settings
from frontend.core.session import SessionState
from frontend.main_window import MainWindow


def _load_stylesheet() -> str:
    path = Path(__file__).resolve().parent / "styles" / "main.qss"
    return path.read_text(encoding="utf-8")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ClinicCare")
    app.setOrganizationName("ClinicManagement")
    app.setStyle("Fusion")
    app.setStyleSheet(_load_stylesheet())

    settings = get_frontend_settings()
    api_client = ApiClient(
        settings.api_base_url,
        timeout=settings.api_timeout_seconds,
    )
    session = SessionState()
    window = MainWindow(api_client, session)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
