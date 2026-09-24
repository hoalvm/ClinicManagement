import React, { useState, useEffect } from 'react';
import { Search, RotateCw, FileText, ChevronRight, Stethoscope, Calendar } from 'lucide-react';
import { storageService } from '../services/storage';
import { PageHeader } from '../components/PageHeader';
import { Pagination } from '../components/Pagination';
import { EmptyState } from '../components/EmptyState';

interface MedicalHistoryViewProps {
  onSelectRecord: (recordId: number) => void;
}

export const MedicalHistoryView: React.FC<MedicalHistoryViewProps> = ({ onSelectRecord }) => {
  const [keyword, setKeyword] = useState('');
  const [page, setPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);
  const [result, setResult] = useState(() =>
    storageService.getMyMedicalRecords({ page: 1, pageSize: 8, keyword: '' })
  );

  const loadData = () => {
    setRefreshing(true);
    const res = storageService.getMyMedicalRecords({ page, pageSize: 8, keyword });
    setResult(res);
    setTimeout(() => setRefreshing(false), 150);
  };

  useEffect(() => {
    loadData();
  }, [page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  return (
    <div id="medical-history-view" className="space-y-6 max-w-6xl mx-auto">
      <PageHeader
        title="Medical History"
        subtitle="Review diagnoses, clinical notes, and care from previous visits."
        actions={
          <button
            id="refresh-records-btn"
            type="button"
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RotateCw className={`w-3.5 h-3.5 text-[#0f766e] ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
        <form onSubmit={handleSearchSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              id="records-search-input"
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="Search diagnosis, symptoms, doctor, or specialty..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
            />
          </div>
          <button
            id="records-search-submit-btn"
            type="submit"
            className="px-5 py-2 text-sm font-medium text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shrink-0"
          >
            Search
          </button>
        </form>
      </div>

      {result.items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No medical records found"
          description={
            keyword
              ? 'No clinical records matched your search query. Try modifying your keywords.'
              : 'You do not have any clinical examination records yet.'
          }
          actionText={keyword ? 'Clear Search' : undefined}
          onAction={() => {
            setKeyword('');
            setPage(1);
          }}
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table id="medical-records-table" className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Examination Date</th>
                  <th className="py-3.5 px-4">Doctor & Specialty</th>
                  <th className="py-3.5 px-4">Diagnosis</th>
                  <th className="py-3.5 px-4">Prescription</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {result.items.map((record) => (
                  <tr
                    key={record.medical_record_id}
                    id={`record-row-${record.medical_record_id}`}
                    onClick={() => onSelectRecord(record.medical_record_id)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 font-medium text-slate-900 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        <span>
                          {new Date(record.examination_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400 pl-6 mt-0.5">
                        {new Date(record.examination_date).toLocaleTimeString('en-US', {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <Stethoscope className="w-3.5 h-3.5 text-[#0f766e]" />
                        {record.doctor.full_name}
                      </div>
                      <div className="text-xs text-slate-500">{record.doctor.specialty}</div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900">{record.diagnosis}</div>
                      <div className="text-xs text-slate-500 line-clamp-1 mt-0.5">{record.symptoms}</div>
                    </td>

                    <td className="py-3.5 px-4">
                      {record.prescription && record.prescription.items.length > 0 ? (
                        <span className="inline-flex items-center px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                          {record.prescription.items.length}{' '}
                          {record.prescription.items.length === 1 ? 'medication' : 'medications'}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">None</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        id={`view-record-btn-${record.medical_record_id}`}
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRecord(record.medical_record_id);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#0f766e] hover:bg-[#d8f3ef] rounded-lg transition-colors"
                      >
                        <span>View Result</span>
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
