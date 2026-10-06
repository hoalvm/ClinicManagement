"""The Admin desktop keeps consultation prices versioned and validates entry."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from frontend.pages.charge_catalog_management import ChargeCatalogManagementPage


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def catalog_page(qt_app: QApplication) -> Iterator[ChargeCatalogManagementPage]:
    page = ChargeCatalogManagementPage()
    page._populate(
        (
            [
                {"code": "CARD-2026-01", "display_name": "Khám tim mạch", "specialty_id": 1,
                 "unit_price": "150000.00", "is_active": False, "effective_from": "2026-01-01T08:00:00"},
                {"code": "CARD-2026-02", "display_name": "Khám tim mạch", "specialty_id": 1,
                 "unit_price": "180000.50", "is_active": True, "effective_from": "2026-10-01T08:00:00"},
                {"code": "SKIN-2026-01", "display_name": "Khám da liễu", "specialty_id": 2,
                 "unit_price": "120000.00", "is_active": True, "effective_from": "2026-10-01T08:00:00"},
            ],
            [
                {"SpecialtyID": 1, "SpecialtyName": "Tim mạch", "IsActive": True},
                {"SpecialtyID": 2, "SpecialtyName": "Da liễu", "IsActive": True},
            ],
        )
    )
    yield page
    page.deleteLater()
    qt_app.processEvents()


def test_catalog_lists_active_and_history_by_specialty(
    catalog_page: ChargeCatalogManagementPage,
) -> None:
    assert catalog_page.table.model().rowCount() == 2
    catalog_page.specialty_filter.setCurrentIndex(catalog_page.specialty_filter.findData(1))
    assert catalog_page.table.model().rowCount() == 1
    assert catalog_page.table.data_model.item(0, 1).text() == "CARD-2026-02"
    assert catalog_page.table.data_model.item(0, 3).text() == "180.000,50 đ"
    catalog_page.status_filter.setCurrentIndex(catalog_page.status_filter.findData("retired"))
    assert catalog_page.table.model().rowCount() == 1
    assert catalog_page.table.data_model.item(0, 1).text() == "CARD-2026-01"


def test_catalog_rejects_blank_fee_without_clearing_form(
    catalog_page: ChargeCatalogManagementPage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = MagicMock()
    monkeypatch.setattr(catalog_page, "run_admin_task", run)
    dialog, specialty, code, name, price = catalog_page._build_create_dialog()
    specialty.setCurrentIndex(specialty.findData(1))
    code.setText("CARD-2026-03")
    name.setText("Khám tim mạch")
    catalog_page._submit_create(dialog, specialty, code, name, price)
    run.assert_not_called()
    assert code.text() == "CARD-2026-03" and name.text() == "Khám tim mạch"
    price.setText("-1000")
    catalog_page._submit_create(dialog, specialty, code, name, price)
    run.assert_not_called()
    dialog.deleteLater()


def test_catalog_posts_new_version_with_exact_decimal_price(
    catalog_page: ChargeCatalogManagementPage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog, specialty, code, name, price = catalog_page._build_create_dialog()
    specialty.setCurrentIndex(specialty.findData(1))
    code.setText("CARD-2026-03")
    name.setText("Khám tim mạch")
    price.setText("190000.50")
    posted: list[tuple[str, dict]] = []

    class Response:
        status_code = 201

    def fake_post(path: str, *, json: dict) -> Response:
        posted.append((path, json))
        return Response()

    from frontend.pages import charge_catalog_management as module

    monkeypatch.setattr(module.api_client, "post", fake_post)
    monkeypatch.setattr(catalog_page, "run_admin_task", lambda _key, operation, _callback, **_kwargs: operation())
    catalog_page._submit_create(dialog, specialty, code, name, price)
    assert posted == [
        (
            "/api/v1/catalog/charges",
            {"code": "CARD-2026-03", "display_name": "Khám tim mạch",
             "category": "CONSULTATION", "specialty_id": 1, "unit_price": "190000.50"},
        )
    ]
    dialog.deleteLater()
