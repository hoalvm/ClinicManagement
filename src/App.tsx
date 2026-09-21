import React, { useState, useEffect } from 'react';
import { Menu, X, Activity } from 'lucide-react';
import { storageService } from './services/storage';
import { NavRoute, Sidebar } from './components/Sidebar';
import { LoginView } from './views/LoginView';
import { RegisterView } from './views/RegisterView';
import { DashboardView } from './views/DashboardView';
import { AppointmentsView } from './views/AppointmentsView';
import { AppointmentDetailView } from './views/AppointmentDetailView';
import { MedicalHistoryView } from './views/MedicalHistoryView';
import { MedicalResultView } from './views/MedicalResultView';
import { InvoiceHistoryView } from './views/InvoiceHistoryView';
import { InvoiceDetailView } from './views/InvoiceDetailView';
import { PatientProfileView } from './views/PatientProfileView';
import { ReceptionDashboard } from './views/ReceptionDashboard';
import { AppointmentManagement } from './views/AppointmentManagement';
import { CheckIn } from './views/CheckIn';
import { BookForPatient } from './views/BookForPatient';
import { InvoiceView } from './views/InvoiceView';
import { PaymentView } from './views/PaymentView';
import { PaymentHistory } from './views/PaymentHistory';

type AppView =
  | 'login'
  | 'register'
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
  | 'appointment_detail'
  | 'medical_history'
  | 'medical_result'
  | 'invoice_history'
  | 'invoice_detail';

export const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState(() => storageService.getCurrentUser());
  const [activeView, setActiveView] = useState<AppView>(() => (currentUser ? 'reception_dashboard' : 'login'));
  const [activeSidebarRoute, setActiveSidebarRoute] = useState<NavRoute>('reception_dashboard');

  const [selectedAppointmentId, setSelectedAppointmentId] = useState<number | null>(null);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<number | null>(null);

  // Reception navigation params
  const [receptionStatusFilter, setReceptionStatusFilter] = useState<string>('ALL');
  const [receptionApptId, setReceptionApptId] = useState<number | undefined>(undefined);
  const [receptionInvoiceId, setReceptionInvoiceId] = useState<number | undefined>(undefined);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authBanner, setAuthBanner] = useState<{
    title: string;
    message: string;
    severity: 'success' | 'info';
  } | null>(null);

  const refreshCurrentUser = () => {
    const user = storageService.getCurrentUser();
    setCurrentUser(user);
    if (!user) {
      setActiveView('login');
    }
  };

  const handleNavigate = (route: NavRoute, params?: any) => {
    setActiveSidebarRoute(route);
    setActiveView(route as AppView);
    if (params) {
      if (params.status) setReceptionStatusFilter(params.status);
      if (params.appointmentId) setReceptionApptId(params.appointmentId);
      if (params.invoiceId) setReceptionInvoiceId(params.invoiceId);
    }
    setMobileMenuOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenAppointment = (appointmentId: number) => {
    setSelectedAppointmentId(appointmentId);
    setActiveSidebarRoute('appointments');
    setActiveView('appointment_detail');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenMedicalRecord = (recordId: number) => {
    setSelectedRecordId(recordId);
    setActiveSidebarRoute('medical_history');
    setActiveView('medical_result');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenInvoice = (invoiceId: number) => {
    setSelectedInvoiceId(invoiceId);
    setActiveSidebarRoute('invoice_history');
    setActiveView('invoice_detail');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLogout = () => {
    storageService.logout();
    setCurrentUser(null);
    setActiveView('login');
    setAuthBanner({
      title: 'Signed Out',
      message: 'You have been safely signed out of ClinicCare.',
      severity: 'info',
    });
  };

  const handleSwitchDemo = (username: 'patient01' | 'patient02') => {
    storageService.switchDemoUser(username);
    const user = storageService.getCurrentUser();
    setCurrentUser(user);
    // Reload dashboard or current view with newly selected account data
    if (activeView === 'appointment_detail' || activeView === 'medical_result' || activeView === 'invoice_detail') {
      setActiveView(activeSidebarRoute);
    }
  };

  // If unauthenticated: Login or Register
  if (!currentUser) {
    if (activeView === 'register') {
      return (
        <RegisterView
          onRegisterSuccess={(username) => {
            setAuthBanner({
              title: 'Account Created',
              message: `Registration complete for @${username}! You can now sign in with your credentials.`,
              severity: 'success',
            });
            setActiveView('login');
          }}
          onBackToLogin={() => {
            setActiveView('login');
          }}
        />
      );
    }

    return (
      <LoginView
        initialMessage={authBanner}
        onLoginSuccess={() => {
          refreshCurrentUser();
          setActiveSidebarRoute('dashboard');
          setActiveView('dashboard');
        }}
        onGoToRegister={() => {
          setActiveView('register');
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8fb] text-slate-800 flex flex-col md:flex-row antialiased">
      {/* Desktop Sidebar */}
      <div className="hidden md:block">
        <Sidebar
          activeRoute={activeSidebarRoute}
          onNavigate={handleNavigate}
          currentUser={currentUser}
          onLogout={handleLogout}
          onSwitchDemo={handleSwitchDemo}
        />
      </div>

      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30 shadow-2xs">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#0f766e] text-white flex items-center justify-center">
            <Activity className="w-5 h-5" />
          </div>
          <span className="font-bold text-slate-900">ClinicCare</span>
        </div>
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-slate-600 hover:text-slate-900 rounded-lg"
          title="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-slate-900/50 flex">
          <div className="w-64 max-w-[80vw] bg-white h-full shadow-2xl">
            <Sidebar
              activeRoute={activeSidebarRoute}
              onNavigate={(route) => {
                handleNavigate(route);
                setMobileMenuOpen(false);
              }}
              currentUser={currentUser}
              onLogout={() => {
                setMobileMenuOpen(false);
                handleLogout();
              }}
              onSwitchDemo={(u) => {
                handleSwitchDemo(u);
                setMobileMenuOpen(false);
              }}
            />
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)} />
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-h-screen">
        {/* Reception & Billing Views */}
        {activeView === 'reception_dashboard' && (
          <ReceptionDashboard
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'appointment_management' && (
          <AppointmentManagement
            initialStatus={receptionStatusFilter}
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'check_in' && (
          <CheckIn
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'book_for_patient' && (
          <BookForPatient
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'invoice_management' && (
          <InvoiceView
            initialAppointmentId={receptionApptId}
            initialStatus={receptionStatusFilter}
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'payment' && (
          <PaymentView
            initialInvoiceId={receptionInvoiceId}
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {activeView === 'payment_history' && (
          <PaymentHistory
            onNavigate={(route, params) => handleNavigate(route as NavRoute, params)}
          />
        )}

        {/* Patient Portal Views */}
        {activeView === 'dashboard' && (
          <DashboardView
            onNavigate={handleNavigate}
            onOpenAppointment={handleOpenAppointment}
          />
        )}

        {activeView === 'profile' && (
          <PatientProfileView onProfileUpdated={refreshCurrentUser} />
        )}

        {activeView === 'appointments' && (
          <AppointmentsView onSelectAppointment={handleOpenAppointment} />
        )}

        {activeView === 'appointment_detail' && selectedAppointmentId && (
          <AppointmentDetailView
            appointmentId={selectedAppointmentId}
            onBack={() => setActiveView('appointments')}
            onOpenMedicalRecord={handleOpenMedicalRecord}
            onOpenInvoice={handleOpenInvoice}
          />
        )}

        {activeView === 'medical_history' && (
          <MedicalHistoryView onSelectRecord={handleOpenMedicalRecord} />
        )}

        {activeView === 'medical_result' && selectedRecordId && (
          <MedicalResultView
            recordId={selectedRecordId}
            onBack={() => setActiveView('medical_history')}
            onOpenAppointment={handleOpenAppointment}
          />
        )}

        {activeView === 'invoice_history' && (
          <InvoiceHistoryView onSelectInvoice={handleOpenInvoice} />
        )}

        {activeView === 'invoice_detail' && selectedInvoiceId && (
          <InvoiceDetailView
            invoiceId={selectedInvoiceId}
            onBack={() => setActiveView('invoice_history')}
            onOpenAppointment={handleOpenAppointment}
          />
        )}
      </main>
    </div>
  );
};

export default App;
