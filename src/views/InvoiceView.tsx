import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Plus,
  CreditCard,
  CheckCircle,
  AlertCircle,
  Trash2,
  X,
  Calendar,
  Receipt,
  Printer,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { Invoice, ReceptionAppointment } from '../types';

interface Props {
  initialAppointmentId?: number;
  initialStatus?: string;
  onNavigate: (view: string, params?: any) => void;
}

export const InvoiceView: React.FC<Props> = ({
  initialAppointmentId,
  initialStatus = 'ALL',
  onNavigate,
}) => {
  const [invoices, setInvoices] = useState<
    Array<Invoice & { patient_name: string; patient_phone: string }>
  >([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [keyword, setKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Create Invoice Dialog
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [eligibleAppointments, setEligibleAppointments] = useState<ReceptionAppointment[]>([]);
  const [selectedApptId, setSelectedApptId] = useState<number>(initialAppointmentId || 0);

  const [items, setItems] = useState<
    Array<{ item_name: string; quantity: number; unit_price: number }>
  >([
    { item_name: 'Tiền công khám chuyên khoa', quantity: 1, unit_price: 200000 },
    { item_name: 'Xét nghiệm máu tổng quát', quantity: 1, unit_price: 350000 },
  ]);

  const loadInvoices = () => {
    setLoading(true);
    try {
      const res = storageService.getReceptionInvoices({
        page,
        pageSize: 10,
        status: statusFilter,
        keyword,
      });
      setInvoices(res.items);
      setTotalPages(res.total_pages);
      setTotalCount(res.total);
    } finally {
      setLoading(false);
    }
  };

  const loadEligibleAppointments = () => {
    // Checked in or confirmed appointments that need billing
    const appts = storageService.getReceptionAppointments({ pageSize: 50 });
    const eligible = appts.items.filter(
      (a) => a.status === 'CHECKED_IN' || a.status === 'CONFIRMED' || a.status === 'COMPLETED'
    );
    setEligibleAppointments(eligible);
    if (initialAppointmentId) {
      setSelectedApptId(initialAppointmentId);
      setShowCreateModal(true);
    } else if (eligible.length > 0 && !selectedApptId) {
      setSelectedApptId(eligible[0].appointment_id);
    }
  };

  useEffect(() => {
    loadInvoices();
    loadEligibleAppointments();
  }, [statusFilter, keyword, page]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const handleAddItem = () => {
    setItems([...items, { item_name: 'Dịch vụ y tế', quantity: 1, unit_price: 100000 }]);
  };

  const handleRemoveItem = (index: number) => {
    if (items.length <= 1) return;
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: string, val: any) => {
    const next = [...items];
    next[index] = { ...next[index], [field]: val };
    setItems(next);
  };

  const calculateTotal = () => {
    return items.reduce((sum, it) => sum + Number(it.unit_price) * Number(it.quantity), 0);
  };

  const handleCreateInvoice = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApptId) return;

    storageService.createInvoiceStaff(selectedApptId, items);
    setShowCreateModal(false);
    loadInvoices();
  };

  return (
    <div id="invoice-view" className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quản Lý Hóa Đơn (Invoices)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Lập hóa đơn viện phí sau khi khám, theo dõi trạng thái chưa thanh toán (UNPAID) và đã thu (PAID).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="btn-open-create-invoice"
            onClick={() => {
              loadEligibleAppointments();
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-bold text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            Lập hóa đơn mới
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-100">
          {[
            { id: 'ALL', label: 'Tất cả hóa đơn' },
            { id: 'UNPAID', label: 'Chưa thanh toán (UNPAID)' },
            { id: 'PAID', label: 'Đã thanh toán (PAID)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                statusFilter === tab.id
                  ? 'bg-orange-600 text-white shadow-sm'
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
            placeholder="Tìm theo mã hóa đơn, tên bệnh nhân, số điện thoại, bác sĩ..."
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500"
          />
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4">Số HĐ</th>
                <th className="py-3.5 px-4">Bệnh nhân</th>
                <th className="py-3.5 px-4">Bác sĩ khám</th>
                <th className="py-3.5 px-4">Ngày tạo</th>
                <th className="py-3.5 px-4">Tổng tiền (VND)</th>
                <th className="py-3.5 px-4">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác thu ngân</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    Không tìm thấy hóa đơn nào.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.invoice_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-700">
                      INV-{String(inv.invoice_id).padStart(5, '0')}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{inv.patient_name}</div>
                      <div className="text-xs text-slate-500">{inv.patient_phone || 'K có SĐT'}</div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-800">
                      {inv.appointment.doctor.full_name}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500">
                      {inv.created_at.slice(0, 10)}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {formatVND(inv.total_amount)}
                    </td>
                    <td className="py-3.5 px-4">
                      {inv.status === 'PAID' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                          Đã thanh toán
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800">
                          Chờ thanh toán (UNPAID)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {inv.status === 'UNPAID' ? (
                          <button
                            onClick={() => onNavigate('payment', { invoiceId: inv.invoice_id })}
                            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md shadow-sm transition-colors"
                          >
                            <CreditCard className="w-3.5 h-3.5" />
                            Thu tiền ngay
                          </button>
                        ) : (
                          <button
                            onClick={() => onNavigate('payment_history', { keyword: String(inv.invoice_id) })}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
                          >
                            <Receipt className="w-3.5 h-3.5" />
                            Xem biên lai
                          </button>
                        )}
                      </div>
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
              Tổng cộng <b>{totalCount}</b> hóa đơn (Trang {page}/{totalPages})
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

      {/* Create Invoice Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-orange-600 font-bold text-base">
                <FileText className="w-5 h-5" />
                <span>Lập hóa đơn viện phí sau khám</span>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 rounded p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateInvoice} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700">Chọn lịch khám cần lập hóa đơn *</label>
                <select
                  value={selectedApptId}
                  onChange={(e) => setSelectedApptId(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 bg-white"
                >
                  {eligibleAppointments.map((a) => (
                    <option key={a.appointment_id} value={a.appointment_id}>
                      #{a.appointment_id} - {a.patient_name} ({a.doctor.full_name} - {a.appointment_date})
                    </option>
                  ))}
                </select>
              </div>

              {/* Line items table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">Chi tiết các khoản thu dịch vụ / thuốc:</span>
                  <button
                    type="button"
                    onClick={handleAddItem}
                    className="text-xs font-semibold text-orange-600 hover:text-orange-700 flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Thêm dòng
                  </button>
                </div>

                <div className="space-y-2">
                  {items.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={item.item_name}
                        onChange={(e) => handleItemChange(idx, 'item_name', e.target.value)}
                        placeholder="Tên dịch vụ/thuốc"
                        className="flex-1 px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-orange-500"
                      />
                      <input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', Number(e.target.value))}
                        className="w-16 px-2 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-orange-500 text-center"
                      />
                      <input
                        type="number"
                        min={0}
                        step={10000}
                        value={item.unit_price}
                        onChange={(e) => handleItemChange(idx, 'unit_price', Number(e.target.value))}
                        className="w-28 px-2 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-orange-500 text-right"
                      />
                      <span className="text-xs font-semibold text-slate-700 w-28 text-right">
                        {formatVND(item.quantity * item.unit_price)}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(idx)}
                        disabled={items.length <= 1}
                        className="p-1.5 text-slate-400 hover:text-rose-600 disabled:opacity-20"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Total Calculation */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-base font-bold text-slate-900">
                <span>Tổng viện phí phải thu (UNPAID):</span>
                <span className="text-xl text-orange-600">{formatVND(calculateTotal())}</span>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-bold text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-sm"
                >
                  Lập hóa đơn (UNPAID)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
