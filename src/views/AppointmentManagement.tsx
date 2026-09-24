import React, { useState, useEffect } from 'react';
import {
  Calendar,
  Clock,
  Search,
  Filter,
  CheckCircle,
  UserCheck,
  CalendarX,
  CalendarClock,
  UserPlus,
  RefreshCw,
  AlertCircle,
  X,
  FileText,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { ReceptionAppointment } from '../types';

interface Props {
  initialStatus?: string;
  onNavigate: (view: string, params?: any) => void;
}

export const AppointmentManagement: React.FC<Props> = ({ initialStatus = 'ALL', onNavigate }) => {
  const [appointments, setAppointments] = useState<ReceptionAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>(initialStatus);
  const [keyword, setKeyword] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Dialog states
  const [cancelTarget, setCancelTarget] = useState<ReceptionAppointment | null>(null);
  const [cancelReason, setCancelReason] = useState('Bệnh nhân bận việc đột xuất');

  const [rescheduleTarget, setRescheduleTarget] = useState<ReceptionAppointment | null>(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('09:00:00');
  const [rescheduleReason, setRescheduleReason] = useState('Dời lịch theo yêu cầu của bệnh nhân');

  const loadAppointments = () => {
    setLoading(true);
    try {
      const res = storageService.getReceptionAppointments({
        page,
        pageSize: 10,
        status: statusFilter,
        keyword,
        date: dateFilter || undefined,
      });
      setAppointments(res.items);
      setTotalPages(res.total_pages);
      setTotalCount(res.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, [statusFilter, keyword, dateFilter, page]);

  const handleConfirm = (id: number) => {
    storageService.confirmAppointmentStaff(id);
    loadAppointments();
  };

  const handleCheckIn = (id: number) => {
    storageService.checkInPatientStaff(id);
    loadAppointments();
  };

  const handleExecuteCancel = () => {
    if (!cancelTarget) return;
    storageService.cancelAppointmentStaff(cancelTarget.appointment_id, cancelReason);
    setCancelTarget(null);
    loadAppointments();
  };

  const handleExecuteReschedule = () => {
    if (!rescheduleTarget || !rescheduleDate) return;
    storageService.rescheduleAppointmentStaff(
      rescheduleTarget.appointment_id,
      rescheduleDate,
      rescheduleTime,
      rescheduleReason
    );
    setRescheduleTarget(null);
    loadAppointments();
  };

  const openRescheduleDialog = (appt: ReceptionAppointment) => {
    setRescheduleTarget(appt);
    setRescheduleDate(appt.appointment_date);
    setRescheduleTime(appt.start_time);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
            Chờ xác nhận
          </span>
        );
      case 'CONFIRMED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
            Đã xác nhận
          </span>
        );
      case 'CHECKED_IN':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
            Đã tiếp nhận
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
            Đã hoàn thành
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
            Đã hủy
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
            {status}
          </span>
        );
    }
  };

  return (
    <div id="appointment-management" className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quản Lý Lịch Hẹn</h1>
          <p className="text-sm text-slate-500 mt-1">
            Xác nhận lịch hẹn, tiếp nhận bệnh nhân đến khám, đổi lịch và hủy lịch.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadAppointments}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Làm mới
          </button>
          <button
            onClick={() => onNavigate('book_for_patient')}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Đặt lịch hộ bệnh nhân
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-100">
          {[
            { id: 'ALL', label: 'Tất cả' },
            { id: 'PENDING', label: 'Chờ duyệt' },
            { id: 'CONFIRMED', label: 'Đã xác nhận' },
            { id: 'CHECKED_IN', label: 'Đã tiếp nhận' },
            { id: 'COMPLETED', label: 'Đã khám' },
            { id: 'CANCELLED', label: 'Đã hủy' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                statusFilter === tab.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search and Date */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          <div className="sm:col-span-8 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Tìm theo tên bệnh nhân, số điện thoại, bác sĩ, lý do khám..."
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
            />
          </div>
          <div className="sm:col-span-4 relative">
            <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => {
                setDateFilter(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
            />
          </div>
        </div>
      </div>

      {/* Appointments Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                <th className="py-3.5 px-4">Mã lịch</th>
                <th className="py-3.5 px-4">Bệnh nhân</th>
                <th className="py-3.5 px-4">Bác sĩ phụ trách</th>
                <th className="py-3.5 px-4">Ngày & Giờ hẹn</th>
                <th className="py-3.5 px-4">Lý do khám</th>
                <th className="py-3.5 px-4">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác quản lý</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {appointments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    Không tìm thấy lịch hẹn nào phù hợp tiêu chí lọc.
                  </td>
                </tr>
              ) : (
                appointments.map((appt) => (
                  <tr key={appt.appointment_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs font-semibold text-slate-600">
                      #{appt.appointment_id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{appt.patient_name}</div>
                      <div className="text-xs text-slate-500">{appt.patient_phone || 'Chưa cập nhật SĐT'}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-slate-800">{appt.doctor.full_name}</div>
                      <div className="text-xs text-slate-500">{appt.doctor.specialty}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-800">{appt.start_time.slice(0, 5)}</div>
                      <div className="text-xs text-slate-500">{appt.appointment_date}</div>
                    </td>
                    <td className="py-3.5 px-4 max-w-[200px] truncate text-slate-600 text-xs">
                      {appt.reason || 'Khám tổng quát'}
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(appt.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5 flex-wrap">
                        {/* 1. Confirm button for PENDING */}
                        {appt.status === 'PENDING' && (
                          <button
                            onClick={() => handleConfirm(appt.appointment_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
                            title="Xác nhận lịch hẹn"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            Xác nhận
                          </button>
                        )}

                        {/* 2. Check-in button for CONFIRMED */}
                        {appt.status === 'CONFIRMED' && (
                          <button
                            onClick={() => handleCheckIn(appt.appointment_id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-purple-700 bg-purple-50 border border-purple-200 rounded-md hover:bg-purple-100 transition-colors"
                            title="Tiếp nhận bệnh nhân khi đến"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                            Tiếp nhận
                          </button>
                        )}

                        {/* 3. Create Invoice button for CHECKED_IN */}
                        {appt.status === 'CHECKED_IN' && (
                          <button
                            onClick={() => onNavigate('invoice_management', { appointmentId: appt.appointment_id })}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-orange-700 bg-orange-50 border border-orange-200 rounded-md hover:bg-orange-100 transition-colors"
                            title="Lập hóa đơn viện phí"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            Lập hóa đơn
                          </button>
                        )}

                        {/* 4. Reschedule button */}
                        {appt.status !== 'CANCELLED' && appt.status !== 'COMPLETED' && (
                          <button
                            onClick={() => openRescheduleDialog(appt)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
                            title="Đổi ngày/giờ hẹn"
                          >
                            <CalendarClock className="w-3.5 h-3.5" />
                            Đổi lịch
                          </button>
                        )}

                        {/* 5. Cancel button */}
                        {appt.status !== 'CANCELLED' && appt.status !== 'COMPLETED' && (
                          <button
                            onClick={() => setCancelTarget(appt)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-rose-600 bg-rose-50 hover:bg-rose-100 rounded-md transition-colors"
                            title="Hủy lịch hẹn"
                          >
                            <CalendarX className="w-3.5 h-3.5" />
                            Hủy
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
              Tổng cộng <b>{totalCount}</b> lịch hẹn (Trang {page}/{totalPages})
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

      {/* Cancel Dialog Modal */}
      {cancelTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-600 font-bold">
                <CalendarX className="w-5 h-5" />
                <span>Xác nhận hủy lịch hẹn</span>
              </div>
              <button
                onClick={() => setCancelTarget(null)}
                className="text-slate-400 hover:text-slate-600 rounded p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-sm text-slate-600">
              Bạn có chắc chắn muốn hủy lịch hẹn <b>#{cancelTarget.appointment_id}</b> của bệnh nhân{' '}
              <b>{cancelTarget.patient_name}</b> vào ngày <b>{cancelTarget.appointment_date}</b> lúc{' '}
              <b>{cancelTarget.start_time.slice(0, 5)}</b>?
            </p>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Lý do hủy:</label>
              <textarea
                rows={2}
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="w-full text-sm p-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setCancelTarget(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Đóng
              </button>
              <button
                onClick={handleExecuteCancel}
                className="px-4 py-2 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm"
              >
                Xác nhận hủy
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reschedule Dialog Modal */}
      {rescheduleTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-blue-600 font-bold">
                <CalendarClock className="w-5 h-5" />
                <span>Đổi ngày / giờ lịch hẹn</span>
              </div>
              <button
                onClick={() => setRescheduleTarget(null)}
                className="text-slate-400 hover:text-slate-600 rounded p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Bệnh nhân: <b>{rescheduleTarget.patient_name}</b> | Bác sĩ: <b>{rescheduleTarget.doctor.full_name}</b>
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700">Ngày hẹn mới:</label>
                <input
                  type="date"
                  value={rescheduleDate}
                  onChange={(e) => setRescheduleDate(e.target.value)}
                  className="w-full mt-1 text-sm p-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Giờ hẹn mới:</label>
                <select
                  value={rescheduleTime}
                  onChange={(e) => setRescheduleTime(e.target.value)}
                  className="w-full mt-1 text-sm p-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
                >
                  {['08:00:00', '08:30:00', '09:00:00', '09:30:00', '10:00:00', '10:30:00', '14:00:00', '14:30:00', '15:00:00', '15:30:00', '16:00:00'].map(
                    (t) => (
                      <option key={t} value={t}>
                        {t.slice(0, 5)}
                      </option>
                    )
                  )}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Lý do dời lịch:</label>
                <input
                  type="text"
                  value={rescheduleReason}
                  onChange={(e) => setRescheduleReason(e.target.value)}
                  className="w-full mt-1 text-sm p-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setRescheduleTarget(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Hủy
              </button>
              <button
                onClick={handleExecuteReschedule}
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
              >
                Lưu thay đổi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
