import React, { useEffect, useState } from 'react';
import {
  Calendar,
  FileText,
  Receipt,
  RotateCw,
  Clock,
  MapPin,
  Stethoscope,
  ChevronRight,
  CreditCard,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { DashboardData } from '../types';
import { PageHeader } from '../components/PageHeader';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import { NavRoute } from '../components/Sidebar';

interface DashboardViewProps {
  onNavigate: (route: NavRoute) => void;
  onOpenAppointment: (id: number) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
  onOpenAppointment,
}) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = () => {
    setRefreshing(true);
    const dash = storageService.getDashboard();
    setData(dash);
    setTimeout(() => setRefreshing(false), 200);
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const upcoming = data?.upcoming_appointment;

  return (
    <div id="dashboard-view" className="space-y-8 max-w-6xl mx-auto">
      <PageHeader
        title={`Hello, ${data?.patient_name || 'Patient'}`}
        subtitle="Here is an overview of your care and your next visit."
        actions={
          <button
            id="dashboard-refresh-btn"
            type="button"
            onClick={loadDashboard}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <RotateCw className={`w-3.5 h-3.5 text-[#0f766e] ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Care overview */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3 tracking-tight">Care Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            id="stat-appointments"
            title="Appointments"
            value={data?.total_appointments ?? 0}
            icon={Calendar}
            tone="blue"
            onClick={() => onNavigate('appointments')}
          />
          <StatCard
            id="stat-medical-records"
            title="Medical Records"
            value={data?.total_medical_records ?? 0}
            icon={FileText}
            tone="violet"
            onClick={() => onNavigate('medical_history')}
          />
          <StatCard
            id="stat-invoices"
            title="Invoices"
            value={data?.total_invoices ?? 0}
            icon={Receipt}
            tone="teal"
            onClick={() => onNavigate('invoice_history')}
          />
          <StatCard
            id="stat-unpaid"
            title="Unpaid Invoices"
            value={data?.unpaid_invoices ?? 0}
            icon={CreditCard}
            tone="amber"
            onClick={() => onNavigate('invoice_history')}
          />
        </div>
      </div>

      {/* Upcoming appointment */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-3 tracking-tight">Upcoming Appointment</h2>
        {upcoming ? (
          <div
            id="upcoming-appointment-card"
            className="bg-white border border-slate-200 rounded-2xl p-6 shadow-2xs hover:border-[#9acdc7] transition-all"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 mb-5 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Your Next Visit
                </span>
                <div className="text-lg font-bold text-slate-900">
                  {upcoming.reason}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={upcoming.status} />
                <button
                  id="view-upcoming-detail-btn"
                  type="button"
                  onClick={() => onOpenAppointment(upcoming.appointment_id)}
                  className="inline-flex items-center gap-1 px-4 py-2 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shadow-xs"
                >
                  <span>View details</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-y-4 gap-x-6 text-sm">
              <div>
                <div className="text-xs text-slate-400 mb-0.5 flex items-center gap-1.5 font-medium">
                  <Stethoscope className="w-3.5 h-3.5 text-[#0f766e]" /> Doctor
                </div>
                <div className="font-semibold text-slate-900">{upcoming.doctor.full_name}</div>
                <div className="text-xs text-slate-500">{upcoming.doctor.specialty}</div>
              </div>

              <div>
                <div className="text-xs text-slate-400 mb-0.5 flex items-center gap-1.5 font-medium">
                  <Calendar className="w-3.5 h-3.5 text-[#0369a1]" /> Date & Time
                </div>
                <div className="font-semibold text-slate-900">
                  {new Date(upcoming.appointment_date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3 h-3 text-slate-400" />
                  {upcoming.start_time} - {upcoming.end_time}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-400 mb-0.5 flex items-center gap-1.5 font-medium">
                  <MapPin className="w-3.5 h-3.5 text-[#6d28d9]" /> Clinic Location
                </div>
                <div className="font-semibold text-slate-900">{upcoming.clinic.clinic_name}</div>
                <div className="text-xs text-slate-500 truncate">{upcoming.clinic.address}</div>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={Calendar}
            title="No upcoming appointments"
            description="Your next confirmed visit will appear here when one is scheduled."
            actionText="Browse Appointments"
            onAction={() => onNavigate('appointments')}
          />
        )}
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div
          onClick={() => onNavigate('appointments')}
          className="p-5 bg-white border border-slate-200 rounded-2xl cursor-pointer hover:border-sky-300 hover:shadow-xs transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-sky-700 uppercase tracking-wider">Appointments</span>
            <Calendar className="w-4 h-4 text-sky-600 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mb-1">Check scheduled visits</div>
          <div className="text-xs text-slate-500">Filter by status, search doctors, and view full visit details.</div>
        </div>

        <div
          onClick={() => onNavigate('medical_history')}
          className="p-5 bg-white border border-slate-200 rounded-2xl cursor-pointer hover:border-purple-300 hover:shadow-xs transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">Medical Records</span>
            <FileText className="w-4 h-4 text-purple-600 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mb-1">Diagnoses & Prescriptions</div>
          <div className="text-xs text-slate-500">Access doctor notes, prescribed medicine dosages, and instructions.</div>
        </div>

        <div
          onClick={() => onNavigate('invoice_history')}
          className="p-5 bg-white border border-slate-200 rounded-2xl cursor-pointer hover:border-teal-300 hover:shadow-xs transition-all group"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-teal-700 uppercase tracking-wider">Billing & Payments</span>
            <Receipt className="w-4 h-4 text-teal-600 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="text-sm font-semibold text-slate-900 mb-1">Track fee statements</div>
          <div className="text-xs text-slate-500">Itemized service fees, payment histories, and outstanding balances.</div>
        </div>
      </div>
    </div>
  );
};
