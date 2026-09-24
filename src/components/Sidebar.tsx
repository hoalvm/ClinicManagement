import React from 'react';
import {
  LayoutDashboard,
  User as UserIcon,
  Calendar,
  FileText,
  Receipt,
  LogOut,
  Users,
  Activity,
  UserCheck,
  UserPlus,
  CreditCard,
  History,
} from 'lucide-react';
import { User, Patient } from '../types';

export type NavRoute =
  | 'reception_dashboard'
  | 'appointment_management'
  | 'check_in'
  | 'book_for_patient'
  | 'invoice_management'
  | 'payment'
  | 'payment_history'
  | 'dashboard'
  | 'profile'
  | 'appointments'
  | 'medical_history'
  | 'invoice_history';

interface SidebarProps {
  activeRoute: NavRoute;
  onNavigate: (route: NavRoute) => void;
  currentUser: { user: User; patient: Patient } | null;
  onLogout: () => void;
  onSwitchDemo: (username: 'patient01' | 'patient02') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeRoute,
  onNavigate,
  currentUser,
  onLogout,
  onSwitchDemo,
}) => {
  const navItems = [
    {
      section: 'TIẾP TÂN & THU NGÂN',
      items: [
        {
          route: 'reception_dashboard' as NavRoute,
          label: 'Bàn Tiếp Tân',
          icon: LayoutDashboard,
        },
        {
          route: 'appointment_management' as NavRoute,
          label: 'Quản Lý Lịch Hẹn',
          icon: Calendar,
        },
        {
          route: 'check_in' as NavRoute,
          label: 'Tiếp Nhận Bệnh Nhân',
          icon: UserCheck,
        },
        {
          route: 'book_for_patient' as NavRoute,
          label: 'Đặt Lịch Hộ',
          icon: UserPlus,
        },
        {
          route: 'invoice_management' as NavRoute,
          label: 'Quản Lý Hóa Đơn',
          icon: FileText,
        },
        {
          route: 'payment' as NavRoute,
          label: 'Quầy Thu Ngân',
          icon: CreditCard,
        },
        {
          route: 'payment_history' as NavRoute,
          label: 'Lịch Sử Thanh Toán',
          icon: History,
        },
      ],
    },
    {
      section: 'CỔNG BỆNH NHÂN',
      items: [
        { route: 'dashboard' as NavRoute, label: 'Dashboard Bệnh Nhân', icon: LayoutDashboard },
        { route: 'profile' as NavRoute, label: 'Hồ Sơ Của Tôi', icon: UserIcon },
        { route: 'appointments' as NavRoute, label: 'Lịch Khám Của Tôi', icon: Calendar },
        { route: 'medical_history' as NavRoute, label: 'Lịch Sử Khám', icon: FileText },
        { route: 'invoice_history' as NavRoute, label: 'Lịch Sử Viện Phí', icon: Receipt },
      ],
    },
  ];

  const currentUsername = currentUser?.user.username || '';
  const alternateUser = currentUsername === 'patient01' ? 'patient02' : 'patient01';
  const alternateName = currentUsername === 'patient01' ? 'Tran Thi Binh' : 'Nguyen Van An';

  return (
    <aside
      id="main-sidebar"
      className="w-64 shrink-0 bg-white border-r border-slate-200 min-h-screen flex flex-col justify-between py-6 px-4 select-none"
    >
      <div>
        {/* Brand */}
        <div className="flex items-center gap-3 px-2 mb-8 cursor-pointer" onClick={() => onNavigate('dashboard')}>
          <div className="w-10 h-10 rounded-xl bg-[#0f766e] text-white flex items-center justify-center shadow-sm shadow-teal-900/10">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="font-extrabold text-slate-900 tracking-tight text-lg leading-none">ClinicCare</div>
            <div className="text-[11px] font-medium text-slate-400 mt-1">Patient Portal</div>
          </div>
        </div>

        {/* Navigation Sections */}
        <div className="space-y-6">
          {navItems.map((group) => (
            <div key={group.section}>
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-3 mb-2">
                {group.section}
              </div>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeRoute === item.route;
                  return (
                    <button
                      key={item.route}
                      id={`nav-btn-${item.route}`}
                      type="button"
                      onClick={() => onNavigate(item.route)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-[#0f766e] text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer / User Context */}
      <div className="pt-6 border-t border-slate-100 space-y-3">
        {/* Demo Switcher Pill */}
        <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200/70">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5 font-medium">
            <span className="flex items-center gap-1">
              <Users className="w-3.5 h-3.5 text-slate-400" />
              Demo Accounts:
            </span>
            <span className="text-[#0f766e] font-semibold">{currentUsername}</span>
          </div>
          <button
            id="switch-demo-btn"
            type="button"
            onClick={() => onSwitchDemo(alternateUser)}
            className="w-full text-left text-xs text-slate-600 hover:text-[#0f766e] hover:bg-white px-2 py-1 rounded-md border border-transparent hover:border-slate-200 transition-all truncate"
            title={`Switch to test account ${alternateUser}`}
          >
            Switch to <span className="font-semibold">{alternateUser}</span> ({alternateName})
          </button>
        </div>

        {/* Current user card */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-9 h-9 rounded-xl bg-[#d8f3ef] text-[#0f766e] font-bold flex items-center justify-center text-sm shrink-0">
            {currentUser?.user.full_name
              ? currentUser.user.full_name
                  .split(' ')
                  .map((n) => n[0])
                  .slice(-2)
                  .join('')
              : 'PT'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold text-slate-900 truncate">
              {currentUser?.user.full_name || 'Patient'}
            </div>
            <div className="text-[11px] text-slate-400 truncate">
              @{currentUser?.user.username || 'patient'}
            </div>
          </div>
        </div>

        {/* Logout Button */}
        <button
          id="logout-btn"
          type="button"
          onClick={onLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium text-slate-600 hover:text-rose-700 hover:bg-rose-50/70 rounded-xl transition-colors"
        >
          <LogOut className="w-4 h-4 text-slate-400" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};
