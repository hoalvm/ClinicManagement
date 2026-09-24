import React, { useState, useEffect } from 'react';
import {
  UserCheck,
  Search,
  Clock,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Users,
  ArrowRight,
  FileText,
  BadgeCheck,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { ReceptionAppointment } from '../types';

interface Props {
  onNavigate: (view: string, params?: any) => void;
}

export const CheckIn: React.FC<Props> = ({ onNavigate }) => {
  const [confirmedQueue, setConfirmedQueue] = useState<ReceptionAppointment[]>([]);
  const [waitingRoomList, setWaitingRoomList] = useState<ReceptionAppointment[]>([]);
  const [selectedAppointment, setSelectedAppointment] = useState<ReceptionAppointment | null>(null);
  const [queueNumber, setQueueNumber] = useState('A-08');
  const [triageNotes, setTriageNotes] = useState('Đã đo sinh hiệu: HA 120/80, SpO2 99%');
  const [searchQuery, setSearchQuery] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = () => {
    const today = new Date().toISOString().split('T')[0];
    const resConfirmed = storageService.getReceptionAppointments({
      status: 'CONFIRMED',
      pageSize: 50,
    });
    setConfirmedQueue(resConfirmed.items);

    const resWaiting = storageService.getReceptionAppointments({
      status: 'CHECKED_IN',
      pageSize: 50,
    });
    setWaitingRoomList(resWaiting.items);

    // Auto select first confirmed if available
    if (resConfirmed.items.length > 0 && !selectedAppointment) {
      setSelectedAppointment(resConfirmed.items[0]);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePerformCheckIn = () => {
    if (!selectedAppointment) return;

    storageService.checkInPatientStaff(
      selectedAppointment.appointment_id,
      queueNumber,
      `Số thứ tự: ${queueNumber} - ${triageNotes}`
    );

    setSuccessMessage(
      `Đã tiếp nhận thành công bệnh nhân ${selectedAppointment.patient_name} (Số thứ tự ${queueNumber})!`
    );
    setSelectedAppointment(null);
    loadData();

    setTimeout(() => {
      setSuccessMessage(null);
    }, 4000);
  };

  const filteredConfirmed = confirmedQueue.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      a.patient_name.toLowerCase().includes(q) ||
      a.patient_phone.includes(q) ||
      String(a.appointment_id).includes(q)
    );
  });

  return (
    <div id="check-in-view" className="space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tiếp Nhận Bệnh Nhân (Check-In)</h1>
        <p className="text-sm text-slate-500 mt-1">
          Ghi nhận bệnh nhân có mặt tại phòng khám, phát số thứ tự hàng đợi và chuyển trạng thái sang ĐÃ TIẾP NHẬN.
        </p>
      </div>

      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm font-medium">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Main Grid: Left is Check-in Form, Right is Waiting Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form & Confirmed Queue */}
        <div className="lg:col-span-7 space-y-6">
          {/* Active Check-In Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div className="flex items-center gap-2 text-purple-700 font-bold">
                <UserCheck className="w-5 h-5" />
                <span>Phiếu tiếp nhận bệnh nhân</span>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 font-medium">
                Bước 3: CHECKED_IN
              </span>
            </div>

            {selectedAppointment ? (
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 rounded-lg border border-slate-200/80 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Họ và tên bệnh nhân:</div>
                    <div className="font-bold text-slate-900 text-base mt-0.5">
                      {selectedAppointment.patient_name}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Số điện thoại:</div>
                    <div className="font-semibold text-slate-800 mt-0.5">
                      {selectedAppointment.patient_phone || 'Chưa có'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Bác sĩ khám:</div>
                    <div className="font-medium text-slate-800 mt-0.5">
                      {selectedAppointment.doctor.full_name} ({selectedAppointment.doctor.specialty})
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 font-medium">Giờ hẹn:</div>
                    <div className="font-medium text-slate-800 mt-0.5">
                      {selectedAppointment.start_time.slice(0, 5)} - {selectedAppointment.appointment_date}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-slate-500 font-medium">Lý do khám:</div>
                    <div className="text-slate-700 mt-0.5 text-xs">{selectedAppointment.reason}</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-700">Cấp số thứ tự khám:</label>
                    <input
                      type="text"
                      value={queueNumber}
                      onChange={(e) => setQueueNumber(e.target.value)}
                      placeholder="VD: A-01, B-12"
                      className="w-full mt-1.5 px-3 py-2 text-sm font-mono font-bold border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-700">Ghi chú tiếp nhận / Sinh hiệu:</label>
                    <input
                      type="text"
                      value={triageNotes}
                      onChange={(e) => setTriageNotes(e.target.value)}
                      placeholder="Đo nhiệt độ, huyết áp..."
                      className="w-full mt-1.5 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                    />
                  </div>
                </div>

                <button
                  id="btn-confirm-check-in"
                  onClick={handlePerformCheckIn}
                  className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg shadow-sm transition-all flex items-center justify-center gap-2"
                >
                  <BadgeCheck className="w-5 h-5" />
                  Xác nhận tiếp nhận bệnh nhân vào phòng chờ
                </button>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-400">
                <AlertCircle className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                Vui lòng chọn một lịch hẹn trong danh sách bên dưới để thực hiện tiếp nhận.
              </div>
            )}
          </div>

          {/* List of Confirmed Appointments awaiting arrival */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">
                Lịch đã xác nhận (Chờ bệnh nhân đến viện) ({filteredConfirmed.length})
              </h2>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Tìm bệnh nhân theo tên, SĐT, mã lịch..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              />
            </div>

            <div className="divide-y divide-slate-100 max-h-[320px] overflow-y-auto">
              {filteredConfirmed.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-400">
                  Không có lịch hẹn nào đang chờ tiếp nhận.
                </div>
              ) : (
                filteredConfirmed.map((appt) => (
                  <div
                    key={appt.appointment_id}
                    onClick={() => setSelectedAppointment(appt)}
                    className={`p-3 rounded-lg cursor-pointer transition-all flex items-center justify-between ${
                      selectedAppointment?.appointment_id === appt.appointment_id
                        ? 'bg-purple-50 border border-purple-200'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-slate-900 text-sm">{appt.patient_name}</div>
                      <div className="text-xs text-slate-500">
                        {appt.start_time.slice(0, 5)} • {appt.doctor.full_name} • {appt.patient_phone || 'K có SĐT'}
                      </div>
                    </div>
                    <button className="px-2.5 py-1 text-xs font-semibold text-purple-700 bg-white border border-purple-200 rounded hover:bg-purple-600 hover:text-white transition-all">
                      Chọn tiếp nhận
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Active Waiting Room List (Checked In) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-600" />
                <h2 className="font-bold text-slate-900 text-sm">Hàng chờ phòng khám (Đã tiếp nhận)</h2>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                {waitingRoomList.length} người
              </span>
            </div>

            <div className="space-y-2.5 max-h-[560px] overflow-y-auto">
              {waitingRoomList.length === 0 ? (
                <div className="py-12 text-center text-slate-400 text-xs">
                  Hiện chưa có bệnh nhân nào trong phòng chờ.
                </div>
              ) : (
                waitingRoomList.map((w, index) => (
                  <div
                    key={w.appointment_id}
                    className="p-3.5 border border-purple-100 bg-purple-50/40 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-purple-600 text-white font-mono text-xs font-bold flex items-center justify-center">
                          {index + 1}
                        </span>
                        <span className="font-bold text-slate-900 text-sm">{w.patient_name}</span>
                      </div>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 bg-white border border-purple-200 text-purple-700 rounded">
                        #{w.appointment_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600">
                      Bác sĩ: <b>{w.doctor.full_name}</b> ({w.doctor.specialty})
                    </div>
                    <div className="text-[11px] text-slate-500 truncate">{w.reason}</div>
                    <div className="pt-1 flex items-center justify-between">
                      <span className="text-[11px] text-purple-700 font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Đang chờ khám
                      </span>
                      <button
                        onClick={() => onNavigate('invoice_management', { appointmentId: w.appointment_id })}
                        className="text-xs font-semibold text-orange-600 hover:text-orange-700 flex items-center gap-1"
                      >
                        <FileText className="w-3.5 h-3.5" /> Lập hóa đơn
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
