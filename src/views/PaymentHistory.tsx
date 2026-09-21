import React, { useState, useEffect } from 'react';
import {
  Receipt,
  Search,
  Filter,
  CreditCard,
  Banknote,
  Printer,
  Calendar,
  Eye,
  X,
  TrendingUp,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { PaymentRecord } from '../types';

interface Props {
  initialKeyword?: string;
  onNavigate: (view: string, params?: any) => void;
}

export const PaymentHistory: React.FC<Props> = ({ initialKeyword = '', onNavigate }) => {
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [keyword, setKeyword] = useState(initialKeyword);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const [viewReceipt, setViewReceipt] = useState<PaymentRecord | null>(null);

  const loadPayments = () => {
    setLoading(true);
    try {
      const res = storageService.getPaymentHistory({
        page,
        pageSize: 10,
        paymentMethod: methodFilter,
        keyword,
      });
      setPayments(res.items);
      setTotalPages(res.total_pages);
      setTotalCount(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPayments();
  }, [methodFilter, keyword, page]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const totalCollected = payments.reduce((sum, p) => sum + p.amount, 0);

  return (
    <div id="payment-history-view" className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Lịch Sử Thu Tiền & Thanh Toán</h1>
          <p className="text-sm text-slate-500 mt-1">
            Nhật ký các giao dịch thu viện phí đã hoàn tất thành công qua Tiền mặt và Thẻ/QR.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-100">
          {[
            { id: 'ALL', label: 'Tất cả hình thức' },
            { id: 'CASH', label: 'Tiền mặt (CASH)' },
            { id: 'CARD', label: 'Thẻ / QR (CARD)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setMethodFilter(tab.id);
                setPage(1);
              }}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                methodFilter === tab.id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm theo số HĐ, tên bệnh nhân, bác sĩ..."
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4">Mã GD</th>
                <th className="py-3.5 px-4">Số hóa đơn</th>
                <th className="py-3.5 px-4">Bệnh nhân</th>
                <th className="py-3.5 px-4">Bác sĩ phụ trách</th>
                <th className="py-3.5 px-4">Thời gian thanh toán</th>
                <th className="py-3.5 px-4">Phương thức</th>
                <th className="py-3.5 px-4">Số tiền thu (VND)</th>
                <th className="py-3.5 px-4 text-right">Biên lai</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {payments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    Chưa có giao dịch thanh toán nào được ghi nhận.
                  </td>
                </tr>
              ) : (
                payments.map((p) => (
                  <tr key={p.payment_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-500">
                      TXN-{String(p.payment_id).slice(-6)}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-700">
                      INV-{String(p.invoice_id).padStart(5, '0')}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">{p.patient_name}</td>
                    <td className="py-3.5 px-4 text-slate-700">{p.doctor_name}</td>
                    <td className="py-3.5 px-4 text-xs text-slate-500">
                      {new Date(p.payment_date).toLocaleString('vi-VN')}
                    </td>
                    <td className="py-3.5 px-4">
                      {p.payment_method === 'CASH' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                          <Banknote className="w-3 h-3" /> Tiền mặt
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                          <CreditCard className="w-3 h-3" /> Thẻ / QR
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-emerald-700">{formatVND(p.amount)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setViewReceipt(p)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Xem biên lai
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>
              Tổng cộng <b>{totalCount}</b> giao dịch (Trang {page}/{totalPages})
            </span>
            <div className="flex gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 border border-slate-200 rounded disabled:opacity-40 hover:bg-slate-50"
              >
                Trước
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 border border-slate-200 rounded disabled:opacity-40 hover:bg-slate-50"
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Receipt Modal */}
      {viewReceipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-emerald-700 font-bold">
                <Receipt className="w-5 h-5" />
                <span>Phiếu thu viện phí</span>
              </div>
              <button
                onClick={() => setViewReceipt(null)}
                className="text-slate-400 hover:text-slate-600 rounded p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div className="text-center pb-2 border-b border-slate-200">
                <div className="font-bold text-sm text-slate-900">PHÒNG KHÁM ĐA KHOA CLINICCARE</div>
                <div className="text-slate-500 text-[11px]">123 Nguyễn Huệ, Quận 1, TP. Hồ Chí Minh</div>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Mã giao dịch:</span>
                <span className="font-mono font-bold">TXN-{String(viewReceipt.payment_id).slice(-6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Hóa đơn tham chiếu:</span>
                <span className="font-mono font-bold">INV-{String(viewReceipt.invoice_id).padStart(5, '0')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Bệnh nhân:</span>
                <span className="font-bold text-slate-900">{viewReceipt.patient_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Bác sĩ khám:</span>
                <span>{viewReceipt.doctor_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Hình thức thanh toán:</span>
                <span className="font-bold">{viewReceipt.payment_method}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Ngày giờ thanh toán:</span>
                <span>{new Date(viewReceipt.payment_date).toLocaleString('vi-VN')}</span>
              </div>
              <div className="pt-2 border-t border-slate-200 flex justify-between items-center text-sm font-bold text-slate-900">
                <span>Số tiền đã thanh toán:</span>
                <span className="text-emerald-700 text-base">{formatVND(viewReceipt.amount)}</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setViewReceipt(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Đóng
              </button>
              <button
                onClick={() => window.print()}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
              >
                <Printer className="w-4 h-4" />
                In biên lai
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
