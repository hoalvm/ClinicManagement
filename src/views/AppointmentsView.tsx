import React, { useState, useEffect } from 'react';
import { Search, RotateCw, Calendar, Clock, MapPin, Stethoscope, ChevronRight } from 'lucide-react';
import { storageService } from '../services/storage';
import { Appointment, AppointmentStatus } from '../types';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { EmptyState } from '../components/EmptyState';

interface AppointmentsViewProps {
  onSelectAppointment: (id: number) => void;
}

export const AppointmentsView: React.FC<AppointmentsViewProps> = ({ onSelectAppointment }) => {
  const [keyword, setKeyword] = useState('');
  const [statusFilter, setStatusFilter] = useState<AppointmentStatus | 'ALL'>('ALL');
  const [page, setPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);
  const [result, setResult] = useState(() =>
    storageService.getMyAppointments({ page: 1, pageSize: 8, keyword: '', status: 'ALL' })
  );

  const loadData = () => {
    setRefreshing(true);
    const res = storageService.getMyAppointments({
      page,
      pageSize: 8,
      keyword,
      status: statusFilter,
    });
    setResult(res);
    setTimeout(() => setRefreshing(false), 150);
  };

  useEffect(() => {
    loadData();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  return (
    <div id="appointments-view" className="space-y-6 max-w-6xl mx-auto">
      <PageHeader
        title="Appointment History"
        subtitle="Find and review your upcoming and previous clinic visits."
        actions={
          <button
            id="refresh-appointments-btn"
            type="button"
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RotateCw className={`w-3.5 h-3.5 text-[#0f766e] ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              id="appointment-search-input"
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="Search doctor, specialty, clinic, or reason..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
            />
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="appointment-status-select" className="text-xs font-semibold text-slate-500 whitespace-nowrap">
              Status:
            </label>
            <select
              id="appointment-status-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as AppointmentStatus | 'ALL');
                setPage(1);
              }}
              className="px-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#0f766e] bg-white text-slate-700"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="CHECKED_IN">Checked In</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>

            <button
              id="appointment-search-submit-btn"
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shrink-0"
            >
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Appointment Table / Cards */}
      {result.items.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No appointments found"
          description={
            keyword || statusFilter !== 'ALL'
              ? 'No appointments matched your search or status filter. Try clearing filters.'
              : 'You do not have any appointment history yet.'
          }
          actionText={keyword || statusFilter !== 'ALL' ? 'Clear Filters' : undefined}
          onAction={() => {
            setKeyword('');
            setStatusFilter('ALL');
            setPage(1);
          }}
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table id="appointments-table" className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Date & Time</th>
                  <th className="py-3.5 px-4">Doctor & Specialty</th>
                  <th className="py-3.5 px-4">Clinic Location</th>
                  <th className="py-3.5 px-4">Reason for Visit</th>
                  <th className="py-3.5 px-4 text-center">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {result.items.map((appt) => (
                  <tr
                    key={appt.appointment_id}
                    id={`appointment-row-${appt.appointment_id}`}
                    onClick={() => onSelectAppointment(appt.appointment_id)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 font-medium text-slate-900 whitespace-nowrap">
                      <div>
                        {new Date(appt.appointment_date).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                      <div className="text-xs text-slate-400 font-normal flex items-center gap-1 mt-0.5">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {appt.start_time} - {appt.end_time}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <Stethoscope className="w-3.5 h-3.5 text-[#0f766e]" />
                        {appt.doctor.full_name}
                      </div>
                      <div className="text-xs text-slate-500">{appt.doctor.specialty}</div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-600">
                      <div className="font-medium text-slate-800">{appt.clinic.clinic_name}</div>
                      <div className="text-xs text-slate-400 truncate max-w-[200px]">{appt.clinic.address}</div>
                    </td>

                    <td className="py-3.5 px-4 text-slate-700 max-w-[240px]">
                      <div className="truncate font-medium">{appt.reason}</div>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={appt.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        id={`view-appt-btn-${appt.appointment_id}`}
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectAppointment(appt.appointment_id);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#0f766e] hover:bg-[#d8f3ef] rounded-lg transition-colors"
                      >
                        <span>Details</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-4 border-t border-slate-100">
            <Pagination
              page={result.page}
              totalPages={result.total_pages}
              totalItems={result.total}
              pageSize={result.page_size}
              onPageChange={(newPage) => setPage(newPage)}
            />
          </div>
        </div>
      )}
    </div>
  );
};
