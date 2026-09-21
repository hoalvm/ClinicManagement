import React from 'react';
import {
  Calendar,
  Stethoscope,
  MapPin,
  Pill,
  Clock,
  ArrowLeft,
  FileCheck2,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { PageHeader } from '../components/PageHeader';
import { EmptyState } from '../components/EmptyState';

interface MedicalResultViewProps {
  recordId: number;
  onBack: () => void;
  onOpenAppointment: (appointmentId: number) => void;
}

export const MedicalResultView: React.FC<MedicalResultViewProps> = ({
  recordId,
  onBack,
  onOpenAppointment,
}) => {
  const record = storageService.getMedicalRecordDetail(recordId);

  if (!record) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <PageHeader title="Medical Record Not Found" onBack={onBack} />
        <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-500">
          The requested medical examination record could not be found.
        </div>
      </div>
    );
  }

  return (
    <div id="medical-result-view" className="space-y-6 max-w-4xl mx-auto">
      <PageHeader
        title={`Medical Result #${record.medical_record_id}`}
        subtitle="A read-only summary of your examination and prescription."
        onBack={onBack}
        actions={
          <button
            id="result-view-appt-btn"
            type="button"
            onClick={() => onOpenAppointment(record.appointment_id)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shadow-2xs"
          >
            <Calendar className="w-4 h-4" />
            <span>View Related Appointment</span>
          </button>
        }
      />

      {/* Examination Summary Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-4 mb-4 border-b border-slate-100">
          <FileCheck2 className="w-4 h-4 text-[#0f766e]" />
          Examination Summary
        </h2>

        <div className="space-y-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pb-4 border-b border-slate-100">
            <div>
              <div className="text-xs text-slate-400 font-semibold mb-0.5">Examination Date</div>
              <div className="font-semibold text-slate-900">
                {new Date(record.examination_date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {new Date(record.examination_date).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-400 font-semibold mb-0.5">Attending Doctor</div>
              <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                <Stethoscope className="w-4 h-4 text-[#0f766e]" />
                {record.doctor.full_name}
              </div>
              <div className="text-xs text-slate-500">{record.doctor.specialty}</div>
            </div>

            {record.clinic && (
              <div className="sm:col-span-2">
                <div className="text-xs text-slate-400 font-semibold mb-0.5">Clinic Location</div>
                <div className="font-medium text-slate-800 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  {record.clinic.clinic_name} — {record.clinic.address}
                </div>
              </div>
            )}
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-1">Symptoms Reported</div>
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-slate-800 text-sm leading-relaxed">
              {record.symptoms || 'None recorded'}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-1">Diagnosis</div>
            <div className="bg-emerald-50/70 p-3 rounded-xl border border-emerald-100 text-emerald-950 font-semibold text-sm leading-relaxed">
              {record.diagnosis}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-1">Clinical Notes & Advice</div>
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 text-slate-700 text-sm leading-relaxed whitespace-pre-line">
              {record.notes || 'No extra clinical notes provided.'}
            </div>
          </div>
        </div>
      </div>

      {/* Prescription Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-4 mb-4 border-b border-slate-100">
          <Pill className="w-4 h-4 text-[#6d28d9]" />
          Prescription
        </h2>

        {record.prescription && record.prescription.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table id="prescription-table" className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Medicine</th>
                  <th className="py-3 px-4 text-center">Quantity</th>
                  <th className="py-3 px-4">Dosage</th>
                  <th className="py-3 px-4">Instructions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {record.prescription.items.map((med, idx) => (
                  <tr key={med.item_id || idx} className="hover:bg-slate-50/50">
                    <td className="py-3.5 px-4 font-semibold text-slate-900">{med.medicine_name}</td>
                    <td className="py-3.5 px-4 text-center font-medium text-slate-700">
                      <span className="px-2 py-0.5 bg-slate-100 rounded-md text-xs font-bold">
                        {med.quantity}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700">{med.dosage}</td>
                    <td className="py-3.5 px-4 text-slate-600 italic">{med.instructions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Pill}
            title="No prescription"
            description="No medication was prescribed for this examination."
          />
        )}
      </div>
    </div>
  );
};
