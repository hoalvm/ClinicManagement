import React from 'react';
import {
  FileText,
  Receipt,
  Calendar,
  Clock,
  Stethoscope,
  MapPin,
  Phone,
  Mail,
  ShieldCheck,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';

interface AppointmentDetailViewProps {
  appointmentId: number;
  onBack: () => void;
  onOpenMedicalRecord: (recordId: number) => void;
  onOpenInvoice: (invoiceId: number) => void;
}

export const AppointmentDetailView: React.FC<AppointmentDetailViewProps> = ({
  appointmentId,
  onBack,
  onOpenMedicalRecord,
  onOpenInvoice,
}) => {
  const appointment = storageService.getAppointmentDetail(appointmentId);

  if (!appointment) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <PageHeader title="Appointment Not Found" onBack={onBack} />
        <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-500">
          The requested appointment could not be located.
        </div>
      </div>
    );
  }

  return (
    <div id="appointment-detail-view" className="space-y-6 max-w-4xl mx-auto">
      <PageHeader
        title={`Appointment #${appointment.appointment_id}`}
        subtitle="Review the visit, care provider, and clinic information."
        onBack={onBack}
        actions={
          <div className="flex items-center gap-2">
            {appointment.medical_record_id && (
              <button
                id="appt-medical-result-btn"
                type="button"
                onClick={() => onOpenMedicalRecord(appointment.medical_record_id!)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-[#0f766e] bg-[#d8f3ef] hover:bg-[#bcebe5] rounded-xl transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span>Medical Result</span>
              </button>
            )}

            {appointment.invoice_id && (
              <button
                id="appt-invoice-btn"
                type="button"
                onClick={() => onOpenInvoice(appointment.invoice_id!)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shadow-2xs"
              >
                <Receipt className="w-4 h-4" />
                <span>View Invoice</span>
              </button>
            )}
          </div>
        }
      />

      {/* Section 1: Appointment Info */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#0f766e]" />
            Appointment Details
          </h2>
          <StatusBadge status={appointment.status} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-sm">
          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Appointment ID</div>
            <div className="font-semibold text-slate-900">#{appointment.appointment_id}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Scheduled Date</div>
            <div className="font-semibold text-slate-900">
              {new Date(appointment.appointment_date).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Time Window</div>
            <div className="font-semibold text-slate-900 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {appointment.start_time} - {appointment.end_time}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Reason for Visit</div>
            <div className="font-semibold text-slate-900">{appointment.reason}</div>
          </div>
        </div>
      </div>

      {/* Section 2: Care Provider */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-4 mb-4 border-b border-slate-100">
          <Stethoscope className="w-4 h-4 text-[#0369a1]" />
          Care Provider
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-sm">
          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Attending Doctor</div>
            <div className="font-semibold text-slate-900">{appointment.doctor.full_name}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Specialty</div>
            <div className="font-semibold text-slate-900">{appointment.doctor.specialty}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">License Number</div>
            <div className="font-semibold text-slate-900 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              {appointment.doctor.license_number || 'Verified Medical License'}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Doctor Contact</div>
            <div className="text-slate-700 space-y-0.5 text-xs">
              {appointment.doctor.phone && (
                <div className="flex items-center gap-1.5">
                  <Phone className="w-3 h-3 text-slate-400" /> {appointment.doctor.phone}
                </div>
              )}
              {appointment.doctor.email && (
                <div className="flex items-center gap-1.5">
                  <Mail className="w-3 h-3 text-slate-400" /> {appointment.doctor.email}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Clinic Information */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-4 mb-4 border-b border-slate-100">
          <MapPin className="w-4 h-4 text-[#6d28d9]" />
          Clinic Information
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-sm">
          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Clinic Name</div>
            <div className="font-semibold text-slate-900">{appointment.clinic.clinic_name}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Clinic Phone</div>
            <div className="font-semibold text-slate-900 flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-slate-400" />
              {appointment.clinic.phone || '02838220001'}
            </div>
          </div>

          <div className="sm:col-span-2">
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Clinic Address</div>
            <div className="font-medium text-slate-700">{appointment.clinic.address}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
