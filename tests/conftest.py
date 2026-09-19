"""Process-wide safe defaults used only while running the test suite."""

import os

# Application settings intentionally fail fast when a signing key is absent.
# Tests use a non-production key before any backend module is imported.
os.environ.setdefault(
    "JWT_SECRET",
    "clinic-management-tests-only-signing-secret-2026",
)

# Qt widget tests run without requiring a visible desktop session.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
