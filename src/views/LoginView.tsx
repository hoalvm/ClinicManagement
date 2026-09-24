import React, { useState } from 'react';
import { Eye, EyeOff, Activity, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { storageService } from '../services/storage';
import { FeedbackBanner } from '../components/FeedbackBanner';

interface LoginViewProps {
  onLoginSuccess: () => void;
  onGoToRegister: () => void;
  initialMessage?: { title: string; message: string; severity: 'success' | 'info' } | null;
}

export const LoginView: React.FC<LoginViewProps> = ({
  onLoginSuccess,
  onGoToRegister,
  initialMessage,
}) => {
  const [username, setUsername] = useState('patient01');
  const [password, setPassword] = useState('Password123!');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      storageService.login(username, password);
      onLoginSuccess();
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePrefill = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
  };

  return (
    <div id="login-screen" className="min-h-screen bg-[#f6f8fb] flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left Hero Banner */}
        <div className="lg:col-span-5 bg-[#123b4a] text-white rounded-3xl p-8 sm:p-10 flex flex-col justify-between shadow-xl shadow-slate-900/10">
          <div>
            <div className="flex items-center gap-3 mb-10">
              <div className="w-10 h-10 rounded-xl bg-[#0f766e] flex items-center justify-center text-white font-black text-xl shadow">
                +
              </div>
              <span className="text-2xl font-bold tracking-tight text-white">ClinicCare</span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight leading-snug mb-4">
              Your health information, in one calm place.
            </h2>
            <p className="text-[#c9e7e5] text-sm leading-relaxed mb-8">
              Review appointments, medical records, prescriptions, and invoices through one secure patient portal.
            </p>

            <div className="space-y-3.5">
              {[
                'Private access to your clinic records',
                'Clear appointment and billing history',
                'Designed for quick, simple follow-up',
              ].map((feat, i) => (
                <div key={i} className="flex items-center gap-3 text-sm text-[#e0f2fe]">
                  <CheckCircle2 className="w-4 h-4 text-[#2dd4bf] shrink-0" />
                  <span>{feat}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-8 mt-8 border-t border-white/10 flex items-center gap-2 text-xs font-semibold tracking-wider text-[#b7d4dd] uppercase">
            <ShieldCheck className="w-4 h-4 text-[#2dd4bf]" />
            <span>Secure Patient Portal</span>
          </div>
        </div>

        {/* Right Form Card */}
        <div className="lg:col-span-7 bg-white rounded-3xl border border-slate-200 p-8 sm:p-10 flex flex-col justify-center shadow-sm">
          <div className="max-w-md mx-auto w-full">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              Welcome Back
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2">Sign in to ClinicCare</h1>
            <p className="text-sm text-slate-500 mb-6">
              Enter your patient account credentials to view your health records.
            </p>

            {initialMessage && (
              <FeedbackBanner
                title={initialMessage.title}
                message={initialMessage.message}
                severity={initialMessage.severity}
                className="mb-5"
              />
            )}

            {error && (
              <FeedbackBanner
                title="Authentication Error"
                message={error}
                severity="error"
                onDismiss={() => setError(null)}
                className="mb-5"
              />
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. patient01"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent transition-all pr-10"
                  />
                  <button
                    id="toggle-password-btn"
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                id="login-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 bg-[#0f766e] hover:bg-[#0d655e] text-white font-semibold rounded-xl text-sm shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:ring-offset-2 disabled:opacity-50"
              >
                {loading ? 'Signing In...' : 'Sign In'}
              </button>
            </form>

            {/* Quick Demo Fill Buttons */}
            <div className="mt-6 pt-6 border-t border-slate-100">
              <div className="text-xs font-medium text-slate-400 mb-2">Test with demo accounts:</div>
              <div className="flex flex-wrap gap-2">
                <button
                  id="fill-demo-patient01"
                  type="button"
                  onClick={() => handlePrefill('patient01', 'Password123!')}
                  className="px-3 py-1.5 text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 font-medium transition-colors"
                >
                  patient01 <span className="text-slate-400 font-normal">(Nguyen Van An)</span>
                </button>
                <button
                  id="fill-demo-patient02"
                  type="button"
                  onClick={() => handlePrefill('patient02', 'Password123!')}
                  className="px-3 py-1.5 text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-slate-700 font-medium transition-colors"
                >
                  patient02 <span className="text-slate-400 font-normal">(Tran Thi Binh)</span>
                </button>
              </div>
            </div>

            <div className="mt-6 text-center text-xs text-slate-500">
              Don't have an account?{' '}
              <button
                id="register-link-btn"
                type="button"
                onClick={onGoToRegister}
                className="text-[#0f766e] hover:underline font-semibold"
              >
                Register as a new patient
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
