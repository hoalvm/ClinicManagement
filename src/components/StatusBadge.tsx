import React from 'react';
import { AppointmentStatus, InvoiceStatus } from '../types';

interface StatusBadgeProps {
  status: AppointmentStatus | InvoiceStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase();

  let label = status;
  let bgClass = 'bg-slate-100 text-slate-700 border-slate-200';

  switch (normalized) {
    case 'CONFIRMED':
      label = 'Confirmed';
      bgClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      break;
    case 'PENDING':
      label = 'Pending';
      bgClass = 'bg-amber-50 text-amber-700 border-amber-200';
      break;
    case 'CHECKED_IN':
      label = 'Checked In';
      bgClass = 'bg-sky-50 text-sky-700 border-sky-200';
      break;
    case 'IN_PROGRESS':
      label = 'In Progress';
      bgClass = 'bg-indigo-50 text-indigo-700 border-indigo-200';
      break;
    case 'COMPLETED':
      label = 'Completed';
      bgClass = 'bg-slate-100 text-slate-700 border-slate-300';
      break;
    case 'CANCELLED':
      label = 'Cancelled';
      bgClass = 'bg-rose-50 text-rose-700 border-rose-200';
      break;
    case 'PAID':
      label = 'Paid';
      bgClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
      break;
    case 'UNPAID':
      label = 'Unpaid';
      bgClass = 'bg-amber-50 text-amber-700 border-amber-300 font-semibold';
      break;
    default:
      label = status;
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span
      id={`status-badge-${normalized.toLowerCase()}`}
      className={`inline-flex items-center justify-center font-medium border rounded-full whitespace-nowrap ${sizeClasses} ${bgClass}`}
    >
      {label}
    </span>
  );
};
