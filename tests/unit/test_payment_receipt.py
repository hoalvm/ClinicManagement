"""Itemized cashier receipt and PDF use the same trusted invoice data."""

from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton

from frontend.api.api_client import ApiClient
from frontend.views.invoice_view import InvoiceManagementView
from frontend.views.payment_view import PaymentView
from frontend.widgets.payment_receipt import receipt_html


def _paid_invoice() -> dict:
    return {
        "invoice_id": 5,
        "appointment_id": 7,
        "created_at": "2026-10-07T11:35:00",
        "appointment_date": "2026-10-07",
        "paid_at": "2026-10-07T11:40:00",
        "status": "PAID",
        "clinic_name": "Phòng khám An Hòa - Tân Bình",
        "clinic_address": "251 Cộng Hòa, Tân Bình, TP. Hồ Chí Minh",
        "patient_name": "Đặng Hoàng Long",
        "doctor_name": "Nguyễn Thị Hoa",
        "total_amount": "250000.00",
        "payment_method": "CASH",
        "amount_received": "300000.00",
        "change_due": "50000.00",
        "items": [
            {
                "item_name": "Khám Da liễu",
                "quantity": 1,
                "unit_price": "250000.00",
                "line_total": "250000.00",
            }
        ],
    }


def test_receipt_escapes_names_and_uses_exact_invoice_lines() -> None:
    invoice = _paid_invoice()
    invoice["patient_name"] = "<script>Đặng Hoàng Long</script>"
    html = receipt_html(invoice)

    assert "&lt;script&gt;Đặng Hoàng Long&lt;/script&gt;" in html
    assert "<script>" not in html
    assert "Phòng khám An Hòa - Tân Bình" in html
    assert "Khám Da liễu" in html
    assert "Tiền trả lại" in html
    assert "CLINICCARE" not in html


def test_paid_invoice_can_be_reopened_from_cashier_list() -> None:
    app = QApplication.instance() or QApplication([])
    view = InvoiceManagementView(MagicMock(spec=ApiClient))
    opened: list[int] = []
    view.view_receipt_requested.connect(opened.append)
    view._on_invoices_loaded(
        {"items": [{**_paid_invoice(), "patient_phone": "0912345678"}], "total": 1, "total_pages": 1}
    )
    button = view.table.indexWidget(view.table.model().index(0, 6)).findChild(QPushButton)
    assert button.text() == "Xem biên lai"
    button.click()
    assert opened == [5]
    view.deleteLater()
    app.processEvents()


def test_receipt_pdf_contains_paid_invoice_and_reopens(
    tmp_path, monkeypatch,
) -> None:
    app = QApplication.instance() or QApplication([])
    view = PaymentView(MagicMock(spec=ApiClient))
    view._show_invoice_details(_paid_invoice())
    assert view.receipt_card.isHidden() is False
    assert view.settlement_card.isHidden()
    assert "Khám Da liễu" in view.receipt_text.toPlainText()
    assert "50.000 ₫" in view.receipt_text.toPlainText()

    output = tmp_path / "receipt.pdf"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(output), "Tệp PDF (*.pdf)"),
    )
    view._save_receipt_pdf()
    assert output.read_bytes().startswith(b"%PDF")
    pdf = QPdfDocument()
    pdf.load(str(output))
    assert pdf.pageCount() == 1
    view.deleteLater()
    app.processEvents()
