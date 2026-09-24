import React, { useState } from 'react';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { storageService } from '../services/storage';
import { FeedbackBanner } from '../components/FeedbackBanner';

interface RegisterViewProps {
  onRegisterSuccess: (username: string) => void;
  onBackToLogin: () => void;
}

export const RegisterView: React.FC<RegisterViewProps> = ({
  onRegisterSuccess,
  onBackToLogin,
}) => {
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    phone: '',
    email: '',
    date_of_birth: '',
    gender: 'MALE',
    address: '',
    password: '',
    confirm_password: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.username.trim()) {
      setError('Username is required');
      return;
    }
    if (!formData.full_name.trim()) {
      setError('Full name is required');
      return;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }
    if (formData.password !== formData.confirm_password) {
      setError('Passwords do not match');
      return;
    }
    if (formData.phone) {
      const cleanPhone = formData.phone.startsWith('+') ? formData.phone.slice(1) : formData.phone;
      if (!/^\d{7,14}$/.test(cleanPhone)) {
        setError('Phone number must contain between 7 and 14 digits');
        return;
      }
    }
    if (formData.date_of_birth) {
      const dob = new Date(formData.date_of_birth);
      if (dob > new Date()) {
        setError('Date of birth cannot be in the future');
        return;
      }
    }

    setLoading(true);
    try {
      storageService.register({
        username: formData.username,
        password: formData.password,
        confirmPassword: formData.confirm_password,
        full_name: formData.full_name,
        phone: formData.phone || undefined,
        email: formData.email || undefined,
        date_of_birth: formData.date_of_birth || undefined,
        gender: formData.gender,
        address: formData.address || undefined,
      });

      onRegisterSuccess(formData.username);
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div id="register-screen" className="min-h-screen bg-[#f6f8fb] flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-2xl bg-white rounded-3xl border border-slate-200 p-8 sm:p-10 shadow-sm">
        <div className="flex items-center justify-between pb-6 mb-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <button
              id="back-to-login-btn"
              type="button"
              onClick={onBackToLogin}
              className="p-2 -ml-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              title="Return to sign in"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Create Patient Account</h1>
              <p className="text-xs text-slate-500 mt-0.5">Enter your details to register with ClinicCare</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#0f766e] bg-[#d8f3ef] px-3 py-1.5 rounded-full font-medium">
            <ShieldCheck className="w-4 h-4" />
            <span>Encrypted Records</span>
          </div>
        </div>

        {error && (
          <FeedbackBanner
            title="Registration Error"
            message={error}
            severity="error"
            onDismiss={() => setError(null)}
            className="mb-6"
          />
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-username">
                Username *
              </label>
              <input
                id="reg-username"
                name="username"
                type="text"
                required
                value={formData.username}
                onChange={handleChange}
                placeholder="Choose a username"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-fullname">
                Full Name *
              </label>
              <input
                id="reg-fullname"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={handleChange}
                placeholder="e.g. Le Van Cuong"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-phone">
                Phone Number
              </label>
              <input
                id="reg-phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                placeholder="e.g. 0900000003"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-email">
                Email Address
              </label>
              <input
                id="reg-email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="patient@example.com"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-dob">
                Date of Birth
              </label>
              <input
                id="reg-dob"
                name="date_of_birth"
                type="date"
                value={formData.date_of_birth}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-gender">
                Gender
              </label>
              <select
                id="reg-gender"
                name="gender"
                value={formData.gender}
                onChange={handleChange}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent bg-white"
              >
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-address">
              Address
            </label>
            <input
              id="reg-address"
              name="address"
              type="text"
              value={formData.address}
              onChange={handleChange}
              placeholder="e.g. 12 Nguyen Trai, District 5, Ho Chi Minh City"
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-password">
                Password (min 8 characters) *
              </label>
              <input
                id="reg-password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                placeholder="Create a password"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1" htmlFor="reg-confirm-password">
                Confirm Password *
              </label>
              <input
                id="reg-confirm-password"
                name="confirm_password"
                type="password"
                required
                value={formData.confirm_password}
                onChange={handleChange}
                placeholder="Repeat password"
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:border-transparent"
              />
            </div>
          </div>

          <div className="pt-4">
            <button
              id="register-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-[#0f766e] hover:bg-[#0d655e] text-white font-semibold rounded-xl text-sm shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-[#0f766e] focus:ring-offset-2 disabled:opacity-50"
            >
              {loading ? 'Creating Account...' : 'Complete Registration'}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center text-xs text-slate-500">
          Already registered?{' '}
          <button
            id="back-login-link-btn"
            type="button"
            onClick={onBackToLogin}
            className="text-[#0f766e] hover:underline font-semibold"
          >
            Sign in to existing account
          </button>
        </div>
      </div>
    </div>
  );
};
