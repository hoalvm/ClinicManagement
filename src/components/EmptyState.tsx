import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div
      id="empty-state-card"
      className="flex flex-col items-center justify-center text-center p-12 bg-white rounded-2xl border border-slate-200"
    >
      <div className="w-14 h-14 rounded-2xl bg-[#d8f3ef] flex items-center justify-center text-[#0f766e] mb-4">
        <Icon className="w-7 h-7" />
      </div>
      <h3 className="text-lg font-bold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm mb-6">{description}</p>
      {actionText && onAction && (
        <button
          id="empty-state-action-btn"
          type="button"
          onClick={onAction}
          className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-xl text-white bg-[#0f766e] hover:bg-[#0d655e] transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
