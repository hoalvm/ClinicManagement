import React, { useState } from 'react';
import {
  Calendar,
  Receipt,
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowLeft,
  DollarSign,
  ShieldCheck,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { PaymentMethod } from '../types';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { FeedbackBanner } from '../components/FeedbackBanner';

interface InvoiceDetailViewProps {
  invoiceId: number;
  onBack: () => void;
  onOpenAppointment: (appointmentId: number) => void;
}

export const InvoiceDetailView: React.FC<InvoiceDetailViewProps> = ({
  invoiceId,
  onBack,
  onOpenAppointment,
}) => {
  const [invoice, setInvoice] = useState(() => storageService.getInvoiceDetail(invoiceId));
  const [paying, setPaying] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('CARD');
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!invoice) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <PageHeader title="Invoice Not Found" onBack={onBack} />
        <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-500">
          The requested invoice record could not be found.
        </div>
      </div>
    );
  }

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  const handlePay = () => {
    try {
      const updated = storageService.payInvoice(invoice.invoice_id, paymentMethod);
      setInvoice(updated);
      setPaying(false);
      setFeedback('Payment completed successfully! Your invoice is now marked as Paid.');
    } catch (err: any) {
      alert(err.message || 'Payment failed');
    }
  };

  return (
    <div id="invoice-detail-view" className="space-y-6 max-w-4xl mx-auto">
      <PageHeader
        title={`Invoice #${invoice.invoice_id}`}
        subtitle="Review billed services, totals, and payment information."
        onBack={onBack}
        actions={
          invoice.appointment_id ? (
            <button
              id="invoice-view-appt-btn"
              type="button"
              onClick={() => onOpenAppointment(invoice.appointment_id)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl transition-colors shadow-2xs"
            >
              <Calendar className="w-4 h-4" />
              <span>View Appointment</span>
            </button>
          ) : undefined
        }
      />

      {feedback && (
        <FeedbackBanner
          title="Payment Successful"
          message={feedback}
          severity="success"
          onDismiss={() => setFeedback(null)}
        />
      )}

      {/* Section 1: Overview */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Receipt className="w-4 h-4 text-[#0f766e]" />
            Invoice Overview
          </h2>
          <StatusBadge status={invoice.status} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-4 gap-x-6 text-sm">
          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Invoice Number</div>
            <div className="font-semibold text-slate-900">#{invoice.invoice_id}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Date Issued</div>
            <div className="font-semibold text-slate-900">
              {new Date(invoice.created_at).toLocaleDateString('en-US', {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </div>
          </div>

          {invoice.appointment && (
            <>
              <div>
                <div className="text-xs text-slate-400 font-semibold mb-0.5">Care Provider</div>
                <div className="font-semibold text-slate-900">{invoice.appointment.doctor.full_name}</div>
              </div>

              <div>
                <div className="text-xs text-slate-400 font-semibold mb-0.5">Appointment Date</div>
                <div className="font-semibold text-slate-900">
                  {invoice.appointment.appointment_date} ({invoice.appointment.start_time})
                </div>
              </div>
            </>
          )}

          <div>
            <div className="text-xs text-slate-400 font-semibold mb-0.5">Total Charges</div>
            <div className="text-xl font-extrabold text-[#0f766e]">
              {formatVND(invoice.total_amount)}
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Line Items */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 pb-4 mb-4 border-b border-slate-100">
          Itemized Services & Medication
        </h2>

        <div className="overflow-x-auto">
          <table id="invoice-items-table" className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4 text-center">Quantity</th>
                <th className="py-3 px-4 text-right">Unit Price</th>
                <th className="py-3 px-4 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoice.items && invoice.items.length > 0 ? (
                invoice.items.map((item) => (
                  <tr key={item.item_id}>
                    <td className="py-3.5 px-4 font-semibold text-slate-900">{item.item_name}</td>
                    <td className="py-3.5 px-4 text-center text-slate-700">{item.quantity}</td>
                    <td className="py-3.5 px-4 text-right text-slate-700">{formatVND(item.unit_price)}</td>
                    <td className="py-3.5 px-4 text-right font-bold text-slate-900">
                      {formatVND(item.line_total)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-4 px-4 text-center text-slate-400">
                    No itemized entries found for this invoice.
                  </td>
                </tr>
              )}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-200 font-bold bg-slate-50/50">
                <td colSpan={3} className="py-3.5 px-4 text-right text-slate-700">
                  Total Due:
                </td>
                <td className="py-3.5 px-4 text-right text-lg text-[#0f766e]">
                  {formatVND(invoice.total_amount)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Section 3: Payment Record / Action */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <h2 className="text-base font-bold text-slate-900 pb-4 mb-4 border-b border-slate-100 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-[#0369a1]" />
            Payment Status
          </span>
          {invoice.status === 'UNPAID' && !paying && (
            <button
              id="pay-invoice-now-btn"
              type="button"
              onClick={() => setPaying(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-xl transition-colors shadow-2xs"
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Settle Payment Now</span>
            </button>
          )}
        </h2>

        {invoice.status === 'PAID' && invoice.payment ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm bg-emerald-50/50 border border-emerald-100 p-5 rounded-xl">
            <div>
              <div className="text-xs text-emerald-800 font-semibold mb-0.5">Payment Method</div>
              <div className="font-bold text-emerald-950 uppercase tracking-wide">
                {invoice.payment.payment_method}
              </div>
            </div>

            <div>
              <div className="text-xs text-emerald-800 font-semibold mb-0.5">Amount Settled</div>
              <div className="font-bold text-emerald-950">
                {formatVND(invoice.payment.amount)}
              </div>
            </div>

            <div>
              <div className="text-xs text-emerald-800 font-semibold mb-0.5">Payment Timestamp</div>
              <div className="font-bold text-emerald-950">
                {new Date(invoice.payment.payment_date).toLocaleString('en-US')}
              </div>
            </div>
          </div>
        ) : paying ? (
          <div className="p-5 border border-amber-200 bg-amber-50/60 rounded-xl space-y-4">
            <div className="font-bold text-slate-900 text-sm">Select Payment Method:</div>
            <div className="grid grid-cols-3 gap-3">
              {(['CARD', 'CASH', 'BANK_TRANSFER'] as PaymentMethod[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setPaymentMethod(m)}
                  className={`p-3 text-xs font-bold rounded-xl border text-center transition-all ${
                    paymentMethod === m
                      ? 'border-[#0f766e] bg-[#d8f3ef] text-[#0f766e]'
                      : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {m.replace('_', ' ')}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setPaying(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 font-medium"
              >
                Cancel
              </button>
              <button
                id="confirm-payment-btn"
                type="button"
                onClick={handlePay}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl shadow-xs"
              >
                Confirm Payment of {formatVND(invoice.total_amount)}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 p-4 bg-amber-50/50 rounded-xl border border-amber-200 text-amber-900 text-sm">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
            <div className="flex-1">
              <span className="font-semibold">Unpaid Balance: </span>
              This invoice is currently pending settlement. Click "Settle Payment Now" to complete payment.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
