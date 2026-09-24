import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  id?: string;
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  tone?: 'teal' | 'blue' | 'violet' | 'amber';
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  id,
  title,
  value,
  subtitle,
  icon: Icon,
  tone = 'teal',
  onClick,
}) => {
  const tones = {
    teal: {
      iconBg: 'bg-[#d8f3ef] text-[#0f766e]',
      valColor: 'text-[#0f766e]',
      borderHover: 'hover:border-[#9acdc7]',
    },
    blue: {
      iconBg: 'bg-[#e0f2fe] text-[#0369a1]',
      valColor: 'text-[#0369a1]',
      borderHover: 'hover:border-sky-300',
    },
    violet: {
      iconBg: 'bg-[#ede9fe] text-[#6d28d9]',
      valColor: 'text-[#6d28d9]',
      borderHover: 'hover:border-purple-300',
    },
    amber: {
      iconBg: 'bg-[#fef3c7] text-[#b45309]',
      valColor: 'text-[#b45309]',
      borderHover: 'hover:border-amber-300',
    },
  }[tone];

  return (
    <div
      id={id || `stat-card-${title.toLowerCase().replace(/\s+/g, '-')}`}
      onClick={onClick}
      className={`p-5 bg-white border border-slate-200 rounded-2xl transition-all duration-200 ${
        onClick ? `cursor-pointer hover:shadow-sm ${tones.borderHover}` : ''
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{title}</div>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${tones.iconBg}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className={`text-3xl font-extrabold tracking-tight ${tones.valColor}`}>{value}</div>
      {subtitle && <div className="text-xs text-slate-400 mt-1">{subtitle}</div>}
    </div>
  );
};
