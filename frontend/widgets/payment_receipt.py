"""One itemized receipt template shared by the desktop preview and PDF export."""

from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

from frontend.views.common import format_date, format_datetime, format_money


def _safe(value: object, fallback: str = "—") -> str:
    return escape(str(value).strip() if value is not None and str(value).strip() else fallback)


def _money(value: object) -> str:
    return escape(format_money(Decimal(str(value or 0))))


def receipt_html(invoice: dict[str, Any]) -> str:
    """Render only server-returned billing facts; never invent a charge or clinic."""

    invoice_id = int(invoice["invoice_id"])
    method = str(invoice.get("payment_method") or "")
    method_name = {
        "CASH": "Tiền mặt",
        "TRANSFER": "Chuyển khoản · xác nhận thủ công",
        "CARD": "Thẻ",
    }.get(method, "—")
    lines = invoice.get("items") or []
    item_rows = "".join(
        "<tr>"
        f"<td style='padding:9px 6px;border-bottom:1px solid #e2e8f0;color:#64748b'>{index}</td>"
        f"<td style='padding:9px 6px;border-bottom:1px solid #e2e8f0'>{_safe(item.get('item_name'))}</td>"
        f"<td align='right' style='padding:9px 6px;border-bottom:1px solid #e2e8f0'>{int(item['quantity'])}</td>"
        f"<td align='right' style='padding:9px 6px;border-bottom:1px solid #e2e8f0'>{_money(item['unit_price'])}</td>"
        f"<td align='right' style='padding:9px 6px;border-bottom:1px solid #e2e8f0'><b>{_money(item['line_total'])}</b></td>"
        "</tr>"
        for index, item in enumerate(lines, start=1)
    )
    if not item_rows:
        item_rows = (
            "<tr><td colspan='5' style='padding:14px;color:#b45309'>"
            "Chưa tải được chi tiết khoản thu. Vui lòng tải lại hóa đơn trước khi lưu PDF."
            "</td></tr>"
        )

    paid_at = format_datetime(invoice.get("paid_at"))
    created_at = format_datetime(invoice.get("created_at"))
    clinic_name = _safe(invoice.get("clinic_name"), "Phòng khám")
    clinic_address = _safe(invoice.get("clinic_address"), "")
    cash_rows = ""
    if method == "CASH":
        cash_rows = (
            "<tr><td>Tiền khách đưa</td><td align='right'>"
            f"{_money(invoice.get('amount_received'))}</td></tr>"
            "<tr><td>Tiền trả lại</td><td align='right'>"
            f"{_money(invoice.get('change_due'))}</td></tr>"
        )
    reference = invoice.get("external_reference")
    reference_row = (
        "<tr><td>Mã giao dịch đối soát</td>"
        f"<td align='right'>{_safe(reference)}</td></tr>"
        if method == "TRANSFER" and reference else ""
    )

    return f"""
    <html><body style="font-family:Arial,'Segoe UI',sans-serif;color:#0f172a;font-size:10pt">
    <table width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td width="60%">
          <div style="font-size:16pt;font-weight:700;color:#0f766e">{clinic_name}</div>
          <div style="color:#64748b;font-size:9pt">{clinic_address}</div>
        </td>
        <td width="40%" align="right" valign="top">
          <div style="font-size:14pt;font-weight:700">BIÊN LAI</div>
          <div style="font-size:9pt;color:#475569">THU PHÍ KHÁM BỆNH</div>
          <div style="color:#64748b">INV-{invoice_id:04d}</div>
        </td>
      </tr>
    </table>
    <hr style="border:0;border-top:2px solid #0f766e;margin-top:16px;margin-bottom:16px">
    <table width="100%" cellspacing="0" cellpadding="3">
      <tr><td width="20%" style="color:#64748b">Bệnh nhân</td><td width="33%"><b>{_safe(invoice.get('patient_name'))}</b></td>
          <td width="20%" style="color:#64748b">Bác sĩ khám</td><td><b>{_safe(invoice.get('doctor_name'))}</b></td></tr>
      <tr><td style="color:#64748b">Mã lịch hẹn</td><td>#{_safe(invoice.get('appointment_id'))}</td>
          <td style="color:#64748b">Ngày khám</td><td>{_safe(format_date(invoice.get('appointment_date')))}</td></tr>
      <tr><td style="color:#64748b">Lập hóa đơn</td><td>{_safe(created_at)}</td>
          <td style="color:#64748b">Thanh toán</td><td>{_safe(paid_at)}</td></tr>
    </table>
    <p style="font-weight:700;margin-top:20px;margin-bottom:7px">CHI TIẾT KHOẢN THU</p>
    <table width="100%" cellspacing="0" cellpadding="0">
      <tr style="background-color:#f1f5f9;color:#334155;font-weight:700">
        <th align="left" width="8%" style="padding:9px 6px">#</th>
        <th align="left" width="40%" style="padding:9px 6px">Nội dung</th>
        <th align="right" width="10%" style="padding:9px 6px">SL</th>
        <th align="right" width="20%" style="padding:9px 6px">Đơn giá</th>
        <th align="right" width="22%" style="padding:9px 6px">Thành tiền</th>
      </tr>
      {item_rows}
    </table>
    <table width="100%" cellspacing="0" cellpadding="5" style="margin-top:14px">
      <tr><td width="60%"><b>TỔNG THANH TOÁN</b></td>
          <td align="right" style="color:#0f766e;font-size:16pt"><b>{_money(invoice.get('total_amount'))}</b></td></tr>
    </table>
    <hr style="border:0;border-top:1px solid #e2e8f0">
    <table width="100%" cellspacing="0" cellpadding="4">
      <tr><td width="60%">Phương thức</td><td align="right">{_safe(method_name)}</td></tr>
      {cash_rows}{reference_row}
      <tr><td>Trạng thái</td><td align="right" style="color:#15803d"><b>ĐÃ THANH TOÁN</b></td></tr>
    </table>
    <p align="center" style="color:#64748b;margin-top:24px;font-size:9pt">
      Cảm ơn Quý khách. Chúc Quý khách mau khỏe!<br>
      Biên lai xác nhận khoản thu của ca khám.
    </p>
    </body></html>
    """
