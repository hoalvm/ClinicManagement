"""The receptionist can find and bill a completed visit without knowing its ID."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from backend.app.schemas.reception import InvoicePreview
from backend.app.services import reception_service as reception_module
from frontend.api.api_client import ApiClient
from frontend.views.invoice_view import InvoiceManagementView


def test_demo_invoice_preview_populates_fee_and_prescription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reception_module,
        "get_settings",
        lambda: SimpleNamespace(app_mode="demo"),
    )
    session = MagicMock()
    session.get.return_value = SimpleNamespace(
        appointment_id=7,
        clinic_id=2,
        status="COMPLETED",
        specialty_id=2,
        appointment_date=date(2026, 10, 7),
        start_time=time(11),
        invoice=None,
        patient=SimpleNamespace(user=SimpleNamespace(full_name="Đặng Hoàng Long")),
        doctor=SimpleNamespace(
            user=SimpleNamespace(full_name="Nguyễn Thị Hoa"),
            specialty=SimpleNamespace(specialty_name="Da liễu"),
        ),
        medical_record=SimpleNamespace(
            symptoms="Mẩn đỏ",
            diagnosis="Viêm da",
            prescription=SimpleNamespace(
                items=[SimpleNamespace(medicine_name="Thuốc A", quantity=2)]
            ),
        ),
    )
    session.scalars.return_value.all.return_value = [
        SimpleNamespace(
            charge_id=4,
            display_name="Khám Da liễu",
            unit_price=Decimal("250000.00"),
        )
    ]

    preview = reception_module.ReceptionService(session).invoice_preview(7)

    assert isinstance(preview, InvoicePreview)
    assert preview.billing_item_name == "Khám Da liễu"
    assert preview.total_amount == Decimal("250000.00")
    assert preview.prescribed_items == [{"medicine_name": "Thuốc A", "quantity": 2}]
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_unbilled_queue_opens_the_selected_visit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    view = InvoiceManagementView(MagicMock(spec=ApiClient))
    opened: list[int] = []
    monkeypatch.setattr(view, "_create_invoice_dialog", opened.append)

    view._on_unbilled_loaded(
        {
            "items": [
                {
                    "appointment_id": 7,
                    "appointment_date": "2026-10-07",
                    "patient": {"full_name": "Đặng Hoàng Long"},
                    "doctor": {"full_name": "Nguyễn Thị Hoa"},
                }
            ],
            "total": 1,
            "total_pages": 1,
        }
    )

    assert view.unbilled_table.item(0, 2).text() == "Đặng Hoàng Long"
    assert view.unbilled_table.item(0, 3).text() == "Nguyễn Thị Hoa"
    button = view.unbilled_table.cellWidget(0, 4)
    assert isinstance(button, QPushButton)
    button.click()
    assert opened == [7]
    view.deleteLater()
    app.processEvents()
