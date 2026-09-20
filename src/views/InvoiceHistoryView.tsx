import React, { useState, useEffect } from 'react';
import { RotateCw, Receipt, ChevronRight, Calendar, DollarSign } from 'lucide-react';
import { storageService } from '../services/storage';
import { Invoice, InvoiceStatus } from '../types';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { EmptyState } from '../components/EmptyState';

interface InvoiceHistoryViewProps {
  onSelectInvoice: (invoiceId: number) => void;
}

export const InvoiceHistoryView: React.FC<InvoiceHistoryViewProps> = ({ onSelectInvoice }) => {
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'ALL'>('ALL');
  const [page, setPage] = useState(1);
  const [refreshing, setRefreshing] = useState(false);
  const [result, setResult] = useState(() =>
    storageService.getMyInvoices({ page: 1, pageSize: 8, status: 'ALL' })
  );

  const loadData = () => {
    setRefreshing(true);
    const res = storageService.getMyInvoices({ page, pageSize: 8, status: statusFilter });
    setResult(res);
    setTimeout(() => setRefreshing(false), 150);
  };

  useEffect(() => {
    loadData();
  }, [page, statusFilter]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  return (
    <div id="invoice-history-view" className="space-y-6 max-w-6xl mx-auto">
      <PageHeader
        title="Invoice History"
        subtitle="Track charges and payment status for your clinic visits."
        actions={
          <button
            id="refresh-invoices-btn"
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
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex items-center justify-between flex-wrap gap-3">
        <div className="text-xs text-slate-500 font-medium">Narrow results by payment status:</div>
        <div className="flex items-center gap-2">
          <label htmlFor="invoice-status-select" className="text-xs font-semibold text-slate-600">
            Status:
          </label>
          <select
            id="invoice-status-select"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as InvoiceStatus | 'ALL');
              setPage(1);
            }}
            className="px-3 py-1.5 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#0f766e] bg-white text-slate-700"
          >
            <option value="ALL">All Invoices</option>
            <option value="PAID">Paid Only</option>
            <option value="UNPAID">Unpaid Only</option>
          </select>
        </div>
      </div>

      {result.items.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="No invoices found"
          description={
            statusFilter !== 'ALL'
              ? 'No invoices match the selected payment status filter.'
              : 'You do not have any billing or invoice records yet.'
          }
          actionText={statusFilter !== 'ALL' ? 'Show All Invoices' : undefined}
          onAction={() => {
            setStatusFilter('ALL');
            setPage(1);
          }}
        />
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table id="invoices-table" className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-4">Invoice #</th>
                  <th className="py-3.5 px-4">Date Issued</th>
                  <th className="py-3.5 px-4">Visit / Doctor</th>
                  <th className="py-3.5 px-4">Total Amount</th>
                  <th className="py-3.5 px-4 text-center">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {result.items.map((inv) => (
                  <tr
                    key={inv.invoice_id}
                    id={`invoice-row-${inv.invoice_id}`}
                    onClick={() => onSelectInvoice(inv.invoice_id)}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      #{inv.invoice_id}
                    </td>

                    <td className="py-3.5 px-4 text-slate-700 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        {new Date(inv.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      {inv.appointment ? (
                        <div>
                          <div className="font-semibold text-slate-900">
                            {inv.appointment.doctor.full_name}
                          </div>
                          <div className="text-xs text-slate-400">
                            Visit date: {inv.appointment.appointment_date}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {formatVND(inv.total_amount)}
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <StatusBadge status={inv.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        id={`view-invoice-btn-${inv.invoice_id}`}
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectInvoice(inv.invoice_id);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#0f766e] hover:bg-[#d8f3ef] rounded-lg transition-colors"
                      >
                        <span>View</span>
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
