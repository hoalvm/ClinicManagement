import React, { useState, useEffect } from 'react';
import {
  UserPlus,
  Search,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  User,
  Phone,
  Check,
  Stethoscope,
  FileText,
  History,
  X,
} from 'lucide-react';
import { storageService } from '../services/storage';

interface Props {
  onNavigate: (view: string, params?: any) => void;
}

export const BookForPatient: React.FC<Props> = ({ onNavigate }) => {
  // Mode: existing search or manual input
  const [phoneSearch, setPhoneSearch] = useState('');
  const [patientId, setPatientId] = useState<number | undefined>(undefined);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [dob, setDob] = useState('1990-01-01');
  const [gender, setGender] = useState('MALE');
  const [address, setAddress] = useState('Quận 1, TP. Hồ Chí Minh');

  // Appointment details
  const [doctorId, setDoctorId] = useState(2);
  const [appointmentDate, setAppointmentDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [startTime, setStartTime] = useState('09:00:00');
  const [reason, setReason] = useState('Đau đầu, mệt mỏi, cần khám kiểm tra');
  const [autoConfirm, setAutoConfirm] = useState(true);

  const [searchResults, setSearchResults] = useState<
    Array<{ patient_id: number; full_name: string; phone: string; gender: string; date_of_birth: string }>
  >([]);
  const [patientHistory, setPatientHistory] = useState<any[]>([]);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(
    null
  );

  const doctorList = [
    { id: 2, name: 'BS. Trần Văn Đức', specialty: 'Tim Mạch (Cardiology)' },
    { id: 3, name: 'BS. Phạm Minh Trí', specialty: 'Nhi Khoa (Pediatrics)' },
    { id: 4, name: 'BS. Lê Thị Mai', specialty: 'Nội Tổng Quát (Internal Medicine)' },
  ];

  const selectedDoctor = doctorList.find((d) => d.id === doctorId) || doctorList[0];

  const handleSearch = (q: string) => {
    setPhoneSearch(q);
    if (q.trim().length >= 2) {
      const res = storageService.searchPatients(q);
      setSearchResults(res);
    } else {
      setSearchResults([]);
    }
  };

  const selectPatient = (p: {
    patient_id: number;
    full_name: string;
    phone: string;
    gender: string;
    date_of_birth: string;
  }) => {
    setPatientId(p.patient_id);
    setFullName(p.full_name);
    setPhone(p.phone);
    setGender(p.gender);
    setDob(p.date_of_birth || '1990-01-01');
    setSearchResults([]);
    setPhoneSearch('');

    // Load past appointments for this patient
    loadPatientHistory(p.patient_id);
  };

  const loadPatientHistory = (ptId: number) => {
    try {
      const allAppts = storageService.getAppointments();
      const patientAppts = allAppts.filter((a) => a.patient_id === ptId);
      setPatientHistory(patientAppts.slice(0, 5));
    } catch {
      setPatientHistory([]);
    }
  };

  const handleClearPatient = () => {
    setPatientId(undefined);
    setFullName('');
    setPhone('');
    setDob('1990-01-01');
    setGender('MALE');
    setAddress('');
    setPatientHistory([]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setStatusMessage({ text: 'Vui lòng nhập họ tên bệnh nhân!', type: 'error' });
      return;
    }
    if (!phone.trim()) {
      setStatusMessage({ text: 'Vui lòng nhập số điện thoại!', type: 'error' });
      return;
    }
    if (!appointmentDate) {
      setStatusMessage({ text: 'Vui lòng chọn ngày khám!', type: 'error' });
      return;
    }

    try {
      const created = storageService.bookForPatient({
        patient_id: patientId,
        full_name: fullName.trim(),
        phone: phone.trim(),
        date_of_birth: dob,
        gender,
        address,
        doctor_id: doctorId,
        appointment_date: appointmentDate,
        start_time: startTime,
        end_time: startTime.replace(':00', ':30'),
        reason,
        auto_confirm: autoConfirm,
      });

      setStatusMessage({
        text: `Đã đặt lịch hẹn thành công cho bệnh nhân ${created.patient_name} (Mã lịch: #${created.appointment_id})!`,
        type: 'success',
      });

      setTimeout(() => {
        onNavigate('appointment_management');
      }, 1500);
    } catch (err: any) {
      setStatusMessage({ text: err.message || 'Lỗi khi đặt lịch hẹn', type: 'error' });
    }
  };

  return (
    <div id="book-for-patient-view" className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Đặt Lịch Cho Bệnh Nhân</h1>
        <p className="text-sm text-slate-500 mt-1">
          Tiếp nhận bệnh nhân qua hotline hoặc trực tiếp tại quầy và thiết lập lịch khám vào hệ thống.
        </p>
      </div>

      {statusMessage && (
        <div
          className={`p-4 rounded-xl flex items-center gap-3 text-sm font-medium ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border border-rose-200 text-rose-800'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Two-Column Grid: Left (Form 60%) & Right ("Thanh bên phải" 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ========================================================================= */}
        {/* LEFT COLUMN: Search & Booking Form (7 cols) */}
        {/* ========================================================================= */}
        <div className="lg:col-span-7 space-y-6">
          {/* Patient Search Bar */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Tìm hồ sơ bệnh nhân cũ (qua SĐT hoặc Tên)
              </label>
              {patientId && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                  Đã chọn #PT-{patientId}
                </span>
              )}
            </div>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Nhập số điện thoại hoặc tên bệnh nhân..."
                value={phoneSearch}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
            </div>

            {searchResults.length > 0 && (
              <div className="p-2 border border-slate-200 rounded-lg bg-slate-50 space-y-1 max-h-48 overflow-y-auto">
                <div className="text-[11px] font-semibold text-slate-500 px-2">Kết quả tìm kiếm:</div>
                {searchResults.map((p) => (
                  <div
                    key={p.patient_id}
                    onClick={() => selectPatient(p)}
                    className="p-2 bg-white rounded border border-slate-100 hover:border-blue-300 hover:bg-blue-50/50 cursor-pointer flex items-center justify-between transition-all"
                  >
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{p.full_name}</span>
                      <span className="text-xs text-slate-500 ml-2">SĐT: {p.phone}</span>
                      {p.date_of_birth && (
                        <span className="text-xs text-slate-400 ml-2">({p.date_of_birth})</span>
                      )}
                    </div>
                    <button
                      type="button"
                      className="px-2.5 py-1 text-xs font-semibold text-blue-600 bg-blue-50 rounded"
                    >
                      Chọn hồ sơ
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
            {/* Patient Details */}
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <User className="w-4 h-4 text-blue-600" />
                  1. Thông tin bệnh nhân
                </h2>
                {patientId ? (
                  <button
                    type="button"
                    onClick={handleClearPatient}
                    className="text-xs text-rose-600 hover:underline font-semibold"
                  >
                    Bỏ chọn (Tạo BN mới)
                  </button>
                ) : (
                  <span className="text-xs text-slate-400">Bệnh nhân mới</span>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Họ và tên bệnh nhân *</label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="VD: Nguyễn Văn An"
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Số điện thoại liên hệ *</label>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="VD: 0912345678"
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Ngày sinh</label>
                  <input
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Giới tính</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
                  >
                    <option value="MALE">Nam</option>
                    <option value="FEMALE">Nữ</option>
                    <option value="OTHER">Khác</option>
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-slate-700">Địa chỉ cư trú</label>
                  <input
                    type="text"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="VD: 123 Nguyễn Thị Minh Khai, Q.3, TP.HCM"
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Appointment Configuration */}
            <div className="space-y-4 pt-2">
              <h2 className="text-sm font-bold text-slate-800 border-b border-slate-100 pb-2 flex items-center gap-2">
                <Stethoscope className="w-4 h-4 text-blue-600" />
                2. Thông tin lịch khám
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Bác sĩ phụ trách *</label>
                  <select
                    value={doctorId}
                    onChange={(e) => setDoctorId(Number(e.target.value))}
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
                  >
                    {doctorList.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.specialty})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700">Ngày khám dự kiến *</label>
                  <input
                    type="date"
                    required
                    value={appointmentDate}
                    onChange={(e) => setAppointmentDate(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700">Khung giờ khám *</label>
                  <select
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
                  >
                    {['08:00:00', '08:30:00', '09:00:00', '09:30:00', '10:00:00', '10:30:00', '13:30:00', '14:00:00', '14:30:00', '15:00:00', '15:30:00', '16:00:00'].map(
                      (t) => (
                        <option key={t} value={t}>
                          {t.slice(0, 5)} - {t.slice(0, 2)}:30
                        </option>
                      )
                    )}
                  </select>
                </div>

                <div className="flex items-center pt-6">
                  <label className="relative flex items-center gap-2 text-sm text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoConfirm}
                      onChange={(e) => setAutoConfirm(e.target.checked)}
                      className="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500"
                    />
                    <span className="font-medium text-xs text-slate-700">Tự động xác nhận lịch (CONFIRMED)</span>
                  </label>
                </div>

                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-slate-700">Lý do khám / Triệu chứng *</label>
                  <textarea
                    rows={2}
                    required
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Mô tả triệu chứng hoặc lý do đến khám..."
                    className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Buttons */}
            <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => onNavigate('appointment_management')}
                className="px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Hủy bỏ
              </button>
              <button
                id="btn-submit-book-patient"
                type="submit"
                className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white bg-teal-700 hover:bg-teal-800 rounded-lg shadow-sm transition-all"
              >
                <Check className="w-4 h-4" />
                Tạo lịch khám
              </button>
            </div>
          </form>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT COLUMN: "Thanh bên phải" - Patient Profile, History & Booking Preview (5 cols) */}
        {/* ========================================================================= */}
        <div className="lg:col-span-5 space-y-6">
          {/* Card 1: Patient Profile Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-600" />
                Hồ sơ bệnh nhân
              </h3>
              {patientId ? (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                  #PT-{patientId} (Đã có hồ sơ)
                </span>
              ) : fullName ? (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                  Bệnh nhân mới
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                  Chưa chọn
                </span>
              )}
            </div>

            {fullName || phone ? (
              <div className="space-y-3 text-sm">
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Họ và tên:</span>
                  <span className="font-bold text-slate-900">{fullName || '—'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Số điện thoại:</span>
                  <span className="font-semibold text-slate-800">{phone || '—'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Ngày sinh:</span>
                  <span className="text-slate-800">{dob || '—'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-50">
                  <span className="text-slate-500">Giới tính:</span>
                  <span className="text-slate-800">
                    {gender === 'MALE' ? 'Nam' : gender === 'FEMALE' ? 'Nữ' : 'Khác'}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Địa chỉ:</span>
                  <span className="text-slate-800 text-right max-w-[200px] truncate">
                    {address || 'Chưa cập nhật'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-6 bg-slate-50 border border-dashed border-slate-200 rounded-lg text-center space-y-2">
                <User className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-xs font-semibold text-slate-600">Chưa có thông tin bệnh nhân</p>
                <p className="text-[11px] text-slate-400">
                  Tìm kiếm bệnh nhân cũ hoặc nhập thông tin bên trái để xem hồ sơ và lịch sử khám.
                </p>
              </div>
            )}
          </div>

          {/* Card 2: Recent Appointment History */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <History className="w-4 h-4 text-teal-600" />
              Lịch sử khám gần đây
            </h3>

            {patientHistory.length > 0 ? (
              <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
                {patientHistory.map((appt) => (
                  <div key={appt.appointment_id} className="py-2.5 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-slate-800">
                        {appt.appointment_date} ({appt.start_time?.slice(0, 5)})
                      </div>
                      <div className="text-slate-500">{appt.doctor?.full_name || 'Bác sĩ'}</div>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        appt.status === 'COMPLETED'
                          ? 'bg-emerald-100 text-emerald-700'
                          : appt.status === 'CONFIRMED'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {appt.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 bg-slate-50 rounded-lg text-center text-xs text-slate-400">
                {patientId
                  ? 'Bệnh nhân chưa có lịch sử khám trước đây.'
                  : 'Chọn bệnh nhân cũ để xem lịch sử các lần khám trước.'}
              </div>
            )}
          </div>

          {/* Card 3: Live Booking Preview */}
          <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-emerald-200/60 pb-2">
              <h3 className="text-sm font-bold text-emerald-950 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-emerald-700" />
                Tóm tắt lịch khám dự kiến
              </h3>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-200 text-emerald-800">
                {autoConfirm ? 'CONFIRMED' : 'PENDING'}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Bác sĩ:</span>
                <span className="font-bold text-emerald-950">{selectedDoctor.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Chuyên khoa:</span>
                <span className="text-emerald-900">{selectedDoctor.specialty}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Thời gian:</span>
                <span className="font-bold text-emerald-950">
                  {startTime.slice(0, 5)}, {appointmentDate}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-emerald-800 font-medium">Bệnh nhân:</span>
                <span className="font-semibold text-emerald-950">
                  {fullName ? `${fullName} ${patientId ? `(#PT-${patientId})` : '(Mới)'}` : 'Chưa nhập'}
                </span>
              </div>
              <div className="pt-1 border-t border-emerald-200/50">
                <span className="text-emerald-800 font-medium">Lý do: </span>
                <span className="text-emerald-900 italic">
                  {reason || 'Tiếp nhận trực tiếp tại quầy'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
