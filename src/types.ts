export type Role = 'PATIENT' | 'DOCTOR' | 'STAFF' | 'ADMIN';

export type Gender = 'MALE' | 'FEMALE' | 'OTHER';

export type AppointmentStatus =
  | 'PENDING'
  | 'CONFIRMED'
  | 'CHECKED_IN'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED';

export type InvoiceStatus = 'UNPAID' | 'PAID';

export type PaymentMethod = 'CASH' | 'CARD';

export interface User {
  user_id: number;
  username: string;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  role: Role;
  is_active: boolean;
  password?: string;
}

export interface Patient {
  patient_id: number;
  user_id: number;
  date_of_birth?: string | null; // YYYY-MM-DD
  gender?: Gender | string | null;
  address?: string | null;
}

export interface Specialty {
  specialty_id: number;
  specialty_name: string;
  description: string;
}

export interface Clinic {
  clinic_id: number;
  clinic_name: string;
  address: string;
  phone: string;
}

export interface Doctor {
  doctor_id: number;
  user_id: number;
  specialty_id: number;
  clinic_id: number;
  license_number: string;
  full_name: string;
  specialty_name: string;
  clinic_name: string;
  clinic_address: string;
  phone?: string | null;
  email?: string | null;
}

export interface Appointment {
  appointment_id: number;
  patient_id: number;
  doctor_id: number;
  clinic_id: number;
  appointment_date: string; // YYYY-MM-DD
  start_time: string; // HH:MM
  end_time: string; // HH:MM
  reason: string;
  status: AppointmentStatus;
  created_at: string;
  doctor: {
    doctor_id: number;
    full_name: string;
    specialty: string;
    phone?: string | null;
    email?: string | null;
    license_number?: string | null;
  };
  clinic: {
    clinic_id: number;
    clinic_name: string;
    address: string;
    phone: string;
  };
  medical_record_id?: number | null;
  invoice_id?: number | null;
}

export interface PrescriptionItem {
  item_id: number;
  medicine_name: string;
  quantity: number;
  dosage: string;
  instructions: string;
}

export interface Prescription {
  prescription_id: number;
  medical_record_id: number;
  created_at: string;
  items: PrescriptionItem[];
}

export interface MedicalRecord {
  medical_record_id: number;
  appointment_id: number;
  patient_id: number;
  examination_date: string; // ISO string
  symptoms: string;
  diagnosis: string;
  notes: string;
  doctor: {
    doctor_id: number;
    full_name: string;
    specialty: string;
  };
  clinic?: {
    clinic_id: number;
    clinic_name: string;
    address: string;
    phone: string;
  } | null;
  prescription?: Prescription | null;
}

export interface InvoiceItem {
  item_id: number;
  item_name: string;
  quantity: number;
  unit_price: number; // In VND, e.g. 200000
  line_total: number;
}

export interface Payment {
  payment_id: number;
  invoice_id: number;
  amount: number;
  payment_method: PaymentMethod;
  payment_date: string; // ISO string
}

export interface Invoice {
  invoice_id: number;
  appointment_id: number;
  patient_id: number;
  created_at: string;
  total_amount: number; // In VND
  status: InvoiceStatus;
  appointment: {
    appointment_date: string;
    start_time: string;
    doctor: {
      doctor_id: number;
      full_name: string;
    };
  };
  items: InvoiceItem[];
  payment?: Payment | null;
}

export interface DashboardData {
  patient_name: string;
  total_appointments: number;
  total_medical_records: number;
  total_invoices: number;
  unpaid_invoices: number;
  upcoming_appointment?: Appointment | null;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReceptionDashboardData {
  today_total: number;
  today_pending: number;
  today_confirmed: number;
  today_checked_in: number;
  today_completed: number;
  unpaid_invoices_count: number;
  unpaid_invoices_amount: number;
  today_revenue: number;
  recent_queue: ReceptionAppointment[];
}

export interface ReceptionAppointment extends Appointment {
  patient_name: string;
  patient_phone: string;
  patient_gender?: string;
  patient_dob?: string;
}

export interface PaymentRecord {
  payment_id: number;
  invoice_id: number;
  amount: number;
  payment_method: PaymentMethod | string;
  payment_date: string;
  patient_name: string;
  doctor_name: string;
  total_amount: number;
}
