import React, { useState, useEffect } from 'react';
import {
  User as UserIcon,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Edit2,
  Check,
  X,
  ShieldCheck,
} from 'lucide-react';
import { storageService } from '../services/storage';
import { PageHeader } from '../components/PageHeader';
import { FeedbackBanner } from '../components/FeedbackBanner';

interface PatientProfileViewProps {
  onProfileUpdated?: () => void;
}

export const PatientProfileView: React.FC<PatientProfileViewProps> = ({ onProfileUpdated }) => {
  const [profile, setProfile] = useState(() => storageService.getCurrentUser());
  const [isEditing, setIsEditing] = useState(false);
  const [feedback, setFeedback] = useState<{ message: string; severity: 'success' | 'error' } | null>(
    null
  );

  const [formData, setFormData] = useState({
    full_name: profile?.user.full_name || '',
    phone: profile?.user.phone || '',
    email: profile?.user.email || '',
    date_of_birth: profile?.patient.date_of_birth || '',
    gender: profile?.patient.gender || 'MALE',
    address: profile?.patient.address || '',
  });

  useEffect(() => {
    const current = storageService.getCurrentUser();
    setProfile(current);
    if (current) {
      setFormData({
        full_name: current.user.full_name || '',
        phone: current.user.phone || '',
        email: current.user.email || '',
        date_of_birth: current.patient.date_of_birth || '',
        gender: current.patient.gender || 'MALE',
        address: current.patient.address || '',
      });
    }
  }, []);

  const handleCancel = () => {
    if (profile) {
      setFormData({
        full_name: profile.user.full_name || '',
        phone: profile.user.phone || '',
        email: profile.user.email || '',
        date_of_birth: profile.patient.date_of_birth || '',
        gender: profile.patient.gender || 'MALE',
        address: profile.patient.address || '',
      });
    }
    setIsEditing(false);
    setFeedback(null);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);

    if (!formData.full_name.trim()) {
      setFeedback({ message: 'Full name cannot be empty.', severity: 'error' });
      return;
    }

    if (formData.phone) {
      const cleanPhone = formData.phone.startsWith('+') ? formData.phone.slice(1) : formData.phone;
      if (!/^\d{7,14}$/.test(cleanPhone)) {
        setFeedback({
          message: 'Phone number must contain between 7 and 14 digits.',
          severity: 'error',
        });
        return;
      }
    }

    try {
      const updated = storageService.updateProfile({
        full_name: formData.full_name,
        phone: formData.phone,
        email: formData.email,
        date_of_birth: formData.date_of_birth,
        gender: formData.gender,
        address: formData.address,
      });

      setProfile(updated);
      setIsEditing(false);
      setFeedback({ message: 'Profile updated successfully.', severity: 'success' });
      if (onProfileUpdated) onProfileUpdated();
    } catch (err: any) {
      setFeedback({ message: err.message || 'Failed to update profile', severity: 'error' });
    }
  };

  if (!profile) {
    return null;
  }

  const initials = profile.user.full_name
    ? profile.user.full_name
        .split(' ')
        .map((n) => n[0])
        .slice(-2)
        .join('')
    : 'PT';

  return (
    <div id="patient-profile-view" className="space-y-6 max-w-4xl mx-auto">
      <PageHeader
        title="My Profile"
        subtitle="Keep your personal and contact information up to date."
        actions={
          !isEditing ? (
            <button
              id="edit-profile-btn"
              type="button"
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-[#0f766e] bg-[#d8f3ef] hover:bg-[#bcebe5] rounded-xl transition-colors"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>Edit Profile</span>
            </button>
          ) : undefined
        }
      />

      {feedback && (
        <FeedbackBanner
          title={feedback.severity === 'success' ? 'Success' : 'Error'}
          message={feedback.message}
          severity={feedback.severity}
          onDismiss={() => setFeedback(null)}
        />
      )}

      {/* Hero Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[#0f766e] text-white font-bold text-xl flex items-center justify-center shadow-sm">
            {initials}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 leading-tight">
              {profile.user.full_name}
            </h2>
            <p className="text-xs text-slate-400 font-medium mt-0.5">
              @{profile.user.username} • Patient Account
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#0f766e] bg-teal-50 px-3 py-1.5 rounded-full border border-teal-100 font-medium">
          <ShieldCheck className="w-4 h-4" />
          <span>Active Patient</span>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Personal Details Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
          <h3 className="text-base font-bold text-slate-900 pb-4 mb-4 border-b border-slate-100">
            Personal Information
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1" htmlFor="profile-username">
                Username (read-only)
              </label>
              <input
                id="profile-username"
                type="text"
                disabled
                value={profile.user.username}
                className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 text-sm cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-fullname">
                Full Name *
              </label>
              <input
                id="profile-fullname"
                type="text"
                required
                disabled={!isEditing}
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-dob">
                Date of Birth
              </label>
              <input
                id="profile-dob"
                type="date"
                disabled={!isEditing}
                value={formData.date_of_birth}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-gender">
                Gender
              </label>
              <select
                id="profile-gender"
                disabled={!isEditing}
                value={formData.gender}
                onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              >
                <option value="MALE">Male</option>
                <option value="FEMALE">Female</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>
        </div>

        {/* Contact Details Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
          <h3 className="text-base font-bold text-slate-900 pb-4 mb-4 border-b border-slate-100">
            Contact Details
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-phone">
                Phone Number
              </label>
              <input
                id="profile-phone"
                type="tel"
                disabled={!isEditing}
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="e.g. 0900000001"
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-email">
                Email Address
              </label>
              <input
                id="profile-email"
                type="email"
                disabled={!isEditing}
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="patient@example.com"
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1" htmlFor="profile-address">
                Residential Address
              </label>
              <input
                id="profile-address"
                type="text"
                disabled={!isEditing}
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Street, ward, district, city"
                className={`w-full px-3.5 py-2 rounded-xl border text-sm transition-all ${
                  isEditing
                    ? 'border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-[#0f766e]'
                    : 'border-slate-200 bg-slate-50 text-slate-800'
                }`}
              />
            </div>
          </div>
        </div>

        {isEditing && (
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              id="cancel-profile-btn"
              type="button"
              onClick={handleCancel}
              className="px-4 py-2.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              id="save-profile-btn"
              type="submit"
              className="inline-flex items-center gap-1.5 px-5 py-2.5 text-xs font-semibold text-white bg-[#0f766e] hover:bg-[#0d655e] rounded-xl shadow-xs transition-colors"
            >
              <Check className="w-4 h-4" />
              <span>Save Changes</span>
            </button>
          </div>
        )}
      </form>
    </div>
  );
};
