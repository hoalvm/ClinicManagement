import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  Banknote,
  CheckCircle2,
  Receipt,
  Search,
  ArrowRight,
  ShieldCheck,
  QrCode,
  Printer,
  Calendar,
  User,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { Invoice, PaymentMethod } from '../types';

interface Props {
  initialInvoiceId?: number;
  onNavigate: (view: string, params?: any) => void;
}

export const PaymentView: React.FC<Props> = ({ initialInvoiceId, onNavigate }) => {
  const [unpaidInvoices, setUnpaidInvoices] = useState<
    Array<Invoice & { patient_name: string; patient_phone: string }>
  >([]);
  const [selectedInvoice, setSelectedInvoice] = useState<
    (Invoice & { patient_name: string; patient_phone: string }) | null
  >(null);
  const [paymentMethod, setPaymentMethod] = useState<'CASH' | 'CARD'>('CASH');
  const [cashTendered, setCashTendered] = useState<number>(0);
  const [paidSuccessInvoice, setPaidSuccessInvoice] = useState<Invoice | null>(null);

  const loadInvoices = () => {
    const res = storageService.getReceptionInvoices({ status: 'UNPAID', pageSize: 50 });
    setUnpaidInvoices(res.items);

    if (initialInvoiceId) {
      const found = res.items.find((i) => i.invoice_id === initialInvoiceId);
      if (found) {
        setSelectedInvoice(found);
        setCashTendered(found.total_amount);
      }
    } else if (res.items.length > 0 && !selectedInvoice) {
      setSelectedInvoice(res.items[0]);
      setCashTendered(res.items[0].total_amount);
    }
  };

  useEffect(() => {
    loadInvoices();
  }, [initialInvoiceId]);

  const handleSelectInvoice = (inv: Invoice & { patient_name: string; patient_phone: string }) => {
    setSelectedInvoice(inv);
    setCashTendered(inv.total_amount);
    setPaidSuccessInvoice(null);
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const handleProcessPayment = () => {
    if (!selectedInvoice) return;

    const paid = storageService.payInvoiceStaff(selectedInvoice.invoice_id, paymentMethod);
    setPaidSuccessInvoice(paid);
    loadInvoices();
  };

  return (
    <div id="payment-view" className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quầy Thu Ngân & Thanh Toán</h1>
        <p className="text-sm text-slate-500 mt-1">
          Thu tiền viện phí trực tiếp bằng Tiền mặt (CASH) hoặc Thẻ / Chuyển khoản (CARD).
        </p>
      </div>

      {/* Main Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: List of UNPAID invoices */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="font-bold text-slate-800 text-sm">Hóa đơn chờ thu ({unpaidInvoices.length})</h2>
              <button
                onClick={loadInvoices}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
              >
                Làm mới
              </button>
            </div>

            <div className="space-y-2.5 max-h-[500px] overflow-y-auto">
              {unpaidInvoices.length === 0 ? (
                <div className="py-12 text-center text-slate-400 text-xs">
                  Không có hóa đơn nào đang chờ thanh toán. Tất cả đã được thanh toán xong!
                </div>
              ) : (
                unpaidInvoices.map((inv) => (
                  <div
                    key={inv.invoice_id}
                    onClick={() => handleSelectInvoice(inv)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      selectedInvoice?.invoice_id === inv.invoice_id
                        ? 'border-emerald-500 bg-emerald-50/50 shadow-sm'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-600">
                        INV-{String(inv.invoice_id).padStart(5, '0')}
                      </span>
                      <span className="font-bold text-emerald-700 text-sm">
                        {formatVND(inv.total_amount)}
                      </span>
                    </div>
                    <div className="font-bold text-slate-900 text-sm mt-1">{inv.patient_name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      BS: {inv.appointment.doctor.full_name} • {inv.created_at.slice(0, 10)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Payment Processing Terminal */}
        <div className="lg:col-span-7 space-y-6">
          {paidSuccessInvoice ? (
            /* Success Receipt Card */
            <div className="bg-white border-2 border-emerald-500 rounded-xl p-6 shadow-md space-y-6 text-center">
              <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Thanh Toán Thành Công!</h2>
                <p className="text-xs text-slate-500 mt-1">
                  Hóa đơn <b>INV-{String(paidSuccessInvoice.invoice_id).padStart(5, '0')}</b> đã chuyển sang
                  trạng thái <span className="text-emerald-600 font-bold">PAID</span>.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-left text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Số hóa đơn:</span>
                  <span className="font-mono font-bold">INV-{String(paidSuccessInvoice.invoice_id).padStart(5, '0')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tổng số tiền:</span>
                  <span className="font-bold text-emerald-700 text-sm">{formatVND(paidSuccessInvoice.total_amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Hình thức thanh toán:</span>
                  <span className="font-semibold">{paidSuccessInvoice.payment?.payment_method}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Thời gian giao dịch:</span>
                  <span>{new Date().toLocaleString('vi-VN')}</span>
                </div>
              </div>

              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  onClick={() => onNavigate('payment_history')}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  <Receipt className="w-4 h-4" />
                  Xem sổ nhật ký thanh toán
                </button>
                <button
                  onClick={() => setPaidSuccessInvoice(null)}
                  className="inline-flex items-center gap-1.5 px-5 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-colors"
                >
                  Tiếp tục thu hóa đơn khác
                </button>
              </div>
            </div>
          ) : selectedInvoice ? (
            /* Active Payment Form */
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-900">
                    Thu tiền: INV-{String(selectedInvoice.invoice_id).padStart(5, '0')}
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Bệnh nhân: <b>{selectedInvoice.patient_name}</b> ({selectedInvoice.patient_phone || 'Không có SĐT'})
                  </p>
                </div>
                <span className="px-3 py-1 rounded-full bg-orange-100 text-orange-800 text-xs font-bold">
                  UNPAID
                </span>
              </div>

              {/* Items Breakdown */}
              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Chi tiết viện phí:
                </div>
                <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 space-y-2 text-xs">
                  {selectedInvoice.items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between">
                      <span className="text-slate-700">
                        {item.item_name} <span className="text-slate-400">x{item.quantity}</span>
                      </span>
                      <span className="font-semibold text-slate-900">{formatVND(item.line_total)}</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t border-slate-200 flex items-center justify-between font-bold text-sm text-slate-900">
                    <span>Tổng cộng:</span>
                    <span className="text-emerald-600 text-lg">{formatVND(selectedInvoice.total_amount)}</span>
                  </div>
                </div>
              </div>

              {/* Payment Method Selector (CASH / CARD) */}
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Phương thức thanh toán:
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CASH')}
                    className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                      paymentMethod === 'CASH'
                        ? 'border-emerald-600 bg-emerald-50/70 text-emerald-800 ring-2 ring-emerald-500/20 shadow-sm'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                    }`}
                  >
                    <Banknote className="w-6 h-6" />
                    <span className="font-bold text-sm">CASH (Tiền mặt)</span>
                    <span className="text-[11px] text-slate-500">Thu tại quầy lễ tân</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPaymentMethod('CARD')}
                    className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                      paymentMethod === 'CARD'
                        ? 'border-blue-600 bg-blue-50/70 text-blue-800 ring-2 ring-blue-500/20 shadow-sm'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                    }`}
                  >
                    <CreditCard className="w-6 h-6" />
                    <span className="font-bold text-sm">CARD (Thẻ / QR)</span>
                    <span className="text-[11px] text-slate-500">POS / Chuyển khoản</span>
                  </button>
                </div>
              </div>

              {/* Cash Tendered Calculator */}
              {paymentMethod === 'CASH' && (
                <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-amber-900">Khách đưa (Tiền mặt):</label>
                    <span className="text-xs text-amber-700">Gợi ý tính tiền thừa</span>
                  </div>
                  <input
                    type="number"
                    step={10000}
                    value={cashTendered}
                    onChange={(e) => setCashTendered(Number(e.target.value))}
                    className="w-full px-3 py-2 text-base font-mono font-bold border border-amber-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/20 bg-white"
                  />
                  <div className="flex items-center justify-between text-xs font-bold text-amber-900 pt-1 border-t border-amber-200">
                    <span>Tiền thừa trả lại:</span>
                    <span className="text-sm font-mono text-emerald-700">
                      {formatVND(Math.max(0, cashTendered - selectedInvoice.total_amount))}
                    </span>
                  </div>
                </div>
              )}

              {paymentMethod === 'CARD' && (
                <div className="p-4 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center gap-3">
                  <QrCode className="w-10 h-10 text-blue-600 shrink-0" />
                  <div className="text-xs text-blue-800">
                    <div className="font-bold">Quẹt thẻ qua máy POS hoặc Quét mã QR thanh toán</div>
                    <div className="text-blue-600 mt-0.5">
                      Hệ thống tự động liên kết tài khoản ngân hàng của phòng khám.
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Payment */}
              <button
                id="btn-confirm-payment"
                onClick={handleProcessPayment}
                className="w-full py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-sm transition-all flex items-center justify-center gap-2 text-base"
              >
                <ShieldCheck className="w-5 h-5" />
                Xác nhận đã thu {formatVND(selectedInvoice.total_amount)} ({paymentMethod} → PAID)
              </button>
            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-400">
              Vui lòng chọn một hóa đơn bên trái để tiến hành thu tiền.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
