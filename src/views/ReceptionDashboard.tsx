import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Clock,
  CheckCircle,
  UserCheck,
  AlertCircle,
  FileText,
  CreditCard,
  TrendingUp,
  UserPlus,
  ArrowRight,
  RefreshCw,
  Search,
  Check,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { ReceptionAppointment, ReceptionDashboardData } from '../types';

interface Props {
  onNavigate: (view: string, params?: any) => void;
}

export const ReceptionDashboard: React.FC<Props> = ({ onNavigate }) => {
  const [data, setData] = useState<ReceptionDashboardData | null>(null);
  const [recentAppointments, setRecentAppointments] = useState<ReceptionAppointment[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    try {
      const stats = storageService.getReceptionDashboard();
      setData(stats);
      const appts = storageService.getReceptionAppointments({ pageSize: 6 });
      setRecentAppointments(appts.items);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleConfirm = (id: number) => {
    storageService.confirmAppointmentStaff(id);
    loadData();
  };

  const handleCheckIn = (id: number) => {
    storageService.checkInPatientStaff(id);
    loadData();
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            Chờ xác nhận
          </span>
        );
      case 'CONFIRMED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Đã xác nhận
          </span>
        );
      case 'CHECKED_IN':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
            Đã tiếp nhận
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            Đã khám
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-100 text-rose-800">
            Đã hủy
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div id="reception-dashboard" className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Bàn Tiếp Tân & Thu Ngân</h1>
          <p className="text-sm text-slate-500 mt-1">
            Quản lý tiếp nhận bệnh nhân, xác nhận lịch hẹn và xử lý thanh toán viện phí.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="btn-refresh-dashboard"
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Làm mới
          </button>
          <button
            id="btn-quick-book"
            onClick={() => onNavigate('book_for_patient')}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Đặt lịch hộ bệnh nhân
          </button>
        </div>
      </div>

      {/* Workflow Process Tracker (Requested Pipeline) */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Quy trình tiếp nhận & thanh toán chuẩn
          </h2>
          <span className="text-xs text-slate-400 font-mono">Quy trình phòng khám</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 items-center text-center">
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="text-xs font-bold text-amber-800">1. PENDING</div>
            <div className="text-[11px] text-amber-600 mt-0.5">Lịch mới đặt</div>
          </div>
          <div className="hidden lg:flex justify-center text-slate-300">
            <ArrowRight className="w-4 h-4" />
          </div>
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-xs font-bold text-blue-800">2. CONFIRMED</div>
            <div className="text-[11px] text-blue-600 mt-0.5">Staff xác nhận</div>
          </div>
          <div className="hidden lg:flex justify-center text-slate-300">
            <ArrowRight className="w-4 h-4" />
          </div>
          <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <div className="text-xs font-bold text-purple-800">3. CHECKED_IN</div>
            <div className="text-[11px] text-purple-600 mt-0.5">Bệnh nhân đến</div>
          </div>
          <div className="hidden lg:flex justify-center text-slate-300">
            <ArrowRight className="w-4 h-4" />
          </div>
          <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
            <div className="text-xs font-bold text-indigo-800">4. COMPLETED</div>
            <div className="text-[11px] text-indigo-600 mt-0.5">Sau khi khám</div>
          </div>
          <div className="hidden lg:flex justify-center text-slate-300">
            <ArrowRight className="w-4 h-4" />
          </div>
          <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <div className="text-xs font-bold text-orange-800">5. UNPAID</div>
            <div className="text-[11px] text-orange-600 mt-0.5">Lập hóa đơn</div>
          </div>
          <div className="hidden lg:flex justify-center text-slate-300">
            <ArrowRight className="w-4 h-4" />
          </div>
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg col-span-2 md:col-span-1">
            <div className="text-xs font-bold text-emerald-800">6. PAID</div>
            <div className="text-[11px] text-emerald-600 mt-0.5">CASH / CARD</div>
          </div>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Today Total */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase">Hẹn hôm nay</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">{data?.today_total || 0}</span>
            <span className="text-xs text-slate-400">lịch khám</span>
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
            <span className="text-amber-600 font-medium">{data?.today_pending || 0} chờ duyệt</span>
            <span>•</span>
            <span className="text-purple-600 font-medium">{data?.today_checked_in || 0} đang chờ khám</span>
          </div>
        </div>

        {/* Pending Approvals */}
        <div
          onClick={() => onNavigate('appointment_management', { status: 'PENDING' })}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm cursor-pointer hover:border-amber-300 hover:shadow transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase">Cần xác nhận</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-amber-600">{data?.today_pending || 0}</span>
            <span className="text-xs text-slate-400">chờ staff xác nhận</span>
          </div>
          <div className="mt-2 text-xs text-blue-600 flex items-center gap-1 font-medium">
            Xử lý ngay <ArrowRight className="w-3 h-3" />
          </div>
        </div>

        {/* Checked In Queue */}
        <div
          onClick={() => onNavigate('check_in')}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm cursor-pointer hover:border-purple-300 hover:shadow transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase">Hàng chờ tiếp nhận</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-purple-600">{data?.today_checked_in || 0}</span>
            <span className="text-xs text-slate-400">bệnh nhân tại viện</span>
          </div>
          <div className="mt-2 text-xs text-purple-600 flex items-center gap-1 font-medium">
            Mở bàn tiếp nhận <ArrowRight className="w-3 h-3" />
          </div>
        </div>

        {/* Revenue & Unpaid Invoices */}
        <div
          onClick={() => onNavigate('invoice_management', { status: 'UNPAID' })}
          className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm cursor-pointer hover:border-emerald-300 hover:shadow transition-all"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase">Hóa đơn chưa thu</span>
            <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center">
              <CreditCard className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-orange-600">{data?.unpaid_invoices_count || 0}</span>
            <span className="text-xs text-slate-400">hóa đơn UNPAID</span>
          </div>
          <div className="mt-2 text-xs text-slate-500 font-medium">
            Tổng nợ: <span className="text-orange-700 font-semibold">{formatVND(data?.unpaid_invoices_amount || 0)}</span>
          </div>
        </div>
      </div>

      {/* Quick Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          id="btn-nav-appointments"
          onClick={() => onNavigate('appointment_management')}
          className="flex items-center justify-center gap-2 p-3.5 bg-white border border-slate-200 rounded-xl hover:bg-blue-50/50 hover:border-blue-200 text-slate-700 font-medium text-sm transition-all shadow-sm"
        >
          <Calendar className="w-4 h-4 text-blue-600" />
          Quản lý lịch hẹn
        </button>
        <button
          id="btn-nav-checkin"
          onClick={() => onNavigate('check_in')}
          className="flex items-center justify-center gap-2 p-3.5 bg-white border border-slate-200 rounded-xl hover:bg-purple-50/50 hover:border-purple-200 text-slate-700 font-medium text-sm transition-all shadow-sm"
        >
          <UserCheck className="w-4 h-4 text-purple-600" />
          Tiếp nhận bệnh nhân
        </button>
        <button
          id="btn-nav-invoices"
          onClick={() => onNavigate('invoice_management')}
          className="flex items-center justify-center gap-2 p-3.5 bg-white border border-slate-200 rounded-xl hover:bg-amber-50/50 hover:border-amber-200 text-slate-700 font-medium text-sm transition-all shadow-sm"
        >
          <FileText className="w-4 h-4 text-amber-600" />
          Quản lý hóa đơn
        </button>
        <button
          id="btn-nav-payment"
          onClick={() => onNavigate('payment')}
          className="flex items-center justify-center gap-2 p-3.5 bg-white border border-slate-200 rounded-xl hover:bg-emerald-50/50 hover:border-emerald-200 text-slate-700 font-medium text-sm transition-all shadow-sm"
        >
          <CreditCard className="w-4 h-4 text-emerald-600" />
          Thu ngân & Thanh toán
        </button>
      </div>

      {/* Recent Appointments & Operational Queue */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Danh sách lịch hẹn cần xử lý</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Thực hiện xác nhận lịch, tiếp nhận bệnh nhân hoặc lập hóa đơn trực tiếp
            </p>
          </div>
          <button
            onClick={() => onNavigate('appointment_management')}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            Xem tất cả lịch hẹn <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/75 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Mã</th>
                <th className="py-3 px-4">Bệnh nhân</th>
                <th className="py-3 px-4">Bác sĩ & Chuyên khoa</th>
                <th className="py-3 px-4">Thời gian</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4 text-right">Hành động nhanh</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {recentAppointments.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    Chưa có lịch hẹn nào cần xử lý.
                  </td>
                </tr>
              ) : (
                recentAppointments.map((appt) => (
                  <tr key={appt.appointment_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-500">#{appt.appointment_id}</td>
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-900">{appt.patient_name}</div>
                      <div className="text-xs text-slate-500">{appt.patient_phone || 'Chưa có SĐT'}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-slate-800">{appt.doctor.full_name}</div>
                      <div className="text-xs text-slate-500">{appt.doctor.specialty}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-800">{appt.start_time.slice(0, 5)}</div>
                      <div className="text-xs text-slate-500">{appt.appointment_date}</div>
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(appt.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {appt.status === 'PENDING' && (
                          <button
                            onClick={() => handleConfirm(appt.appointment_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
                            title="Xác nhận lịch hẹn"
                          >
                            <Check className="w-3.5 h-3.5" />
                            Xác nhận
                          </button>
                        )}
                        {appt.status === 'CONFIRMED' && (
                          <button
                            onClick={() => handleCheckIn(appt.appointment_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded hover:bg-purple-100 transition-colors"
                            title="Tiếp nhận bệnh nhân đến phòng khám"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                            Tiếp nhận
                          </button>
                        )}
                        {appt.status === 'CHECKED_IN' && (
                          <button
                            onClick={() => onNavigate('invoice_management', { appointmentId: appt.appointment_id })}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded hover:bg-orange-100 transition-colors"
                            title="Lập hóa đơn sau khi khám"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            Lập hóa đơn
                          </button>
                        )}
                        <button
                          onClick={() => onNavigate('appointment_management', { selectedId: appt.appointment_id })}
                          className="px-2 py-1 text-xs text-slate-500 hover:text-slate-800 rounded hover:bg-slate-100"
                        >
                          Chi tiết
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
