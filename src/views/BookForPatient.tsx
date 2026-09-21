import React, { useState } from 'react';
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
  ArrowRight,
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
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(
    null
  );

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
    setDob(p.date_of_birth);
    setSearchResults([]);
    setPhoneSearch('');
  };

  const handleClearPatient = () => {
    setPatientId(undefined);
    setFullName('');
    setPhone('');
    setDob('1990-01-01');
    setGender('MALE');
    setAddress('');
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
    <div id="book-for-patient-view" className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Đặt Lịch Hộ Bệnh Nhân</h1>
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

      {/* Patient Search Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
        <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          Tìm hồ sơ bệnh nhân cũ (nhanh qua SĐT hoặc Tên)
        </label>
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
          <div className="p-2 border border-slate-200 rounded-lg bg-slate-50 space-y-1">
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
              Thông tin bệnh nhân {patientId && <span className="text-xs font-mono text-blue-600">(Đã chọn ID #{patientId})</span>}
            </h2>
            {patientId && (
              <button
                type="button"
                onClick={handleClearPatient}
                className="text-xs text-rose-600 hover:underline"
              >
                Nhập bệnh nhân mới
              </button>
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
              <label className="text-xs font-semibold text-slate-700">Ngày tháng năm sinh</label>
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
            Thông tin lịch khám
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700">Chọn Bác sĩ phụ trách *</label>
              <select
                value={doctorId}
                onChange={(e) => setDoctorId(Number(e.target.value))}
                className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
              >
                <option value={2}>BS. Trần Văn Đức - Tim Mạch (Cardiology)</option>
                <option value={3}>BS. Phạm Minh Trí - Nhi Khoa (Pediatrics)</option>
                <option value={4}>BS. Lê Thị Mai - Nội Tổng Quát (Internal Medicine)</option>
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
                {['08:00:00', '08:30:00', '09:00:00', '09:30:00', '10:00:00', '10:30:00', '14:00:00', '14:30:00', '15:00:00', '15:30:00', '16:00:00'].map(
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
                <span className="font-medium">Tự động xác nhận lịch ngay (CONFIRMED)</span>
              </label>
            </div>

            <div className="sm:col-span-2">
              <label className="text-xs font-semibold text-slate-700">Lý do khám / Triệu chứng lâm sàng *</label>
              <textarea
                rows={2}
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="VD: Đau ngực trái khi gắng sức, hồi hộp, khó thở..."
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
            className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-all"
          >
            <Check className="w-4 h-4" />
            Tạo và lưu lịch khám
          </button>
        </div>
      </form>
    </div>
  );
};
