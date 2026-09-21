import {
  users as initialUsers,
  patients as initialPatients,
  appointments as initialAppointments,
  medicalRecords as initialMedicalRecords,
  invoices as initialInvoices,
} from '../data/seedData';
import {
  Appointment,
  AppointmentStatus,
  DashboardData,
  Invoice,
  InvoiceItem,
  InvoiceStatus,
  MedicalRecord,
  PageResponse,
  Patient,
  PaymentMethod,
  PaymentRecord,
  ReceptionAppointment,
  ReceptionDashboardData,
  User,
} from '../types';

const STORAGE_KEYS = {
  USERS: 'clinic_users_v1',
  PATIENTS: 'clinic_patients_v1',
  APPOINTMENTS: 'clinic_appointments_v1',
  MEDICAL_RECORDS: 'clinic_medical_records_v1',
  INVOICES: 'clinic_invoices_v1',
  CURRENT_USER_ID: 'clinic_current_user_id_v1',
  TOKEN: 'clinic_access_token_v1',
};

function loadOrInit<T>(key: string, initial: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    console.warn(`Error loading ${key} from storage:`, e);
  }
  try {
    localStorage.setItem(key, JSON.stringify(initial));
  } catch {}
  return initial;
}

function save<T>(key: string, val: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error(`Error saving ${key} to storage:`, e);
  }
}

class ClinicStorageService {
  private users: User[];
  private patients: Patient[];
  private appointments: Appointment[];
  private medicalRecords: MedicalRecord[];
  private invoices: Invoice[];
  private currentUserId: number | null;
  private token: string | null;

  constructor() {
    this.users = loadOrInit(STORAGE_KEYS.USERS, initialUsers);
    this.patients = loadOrInit(STORAGE_KEYS.PATIENTS, initialPatients);
    this.appointments = loadOrInit(STORAGE_KEYS.APPOINTMENTS, initialAppointments);
    this.medicalRecords = loadOrInit(STORAGE_KEYS.MEDICAL_RECORDS, initialMedicalRecords);
    this.invoices = loadOrInit(STORAGE_KEYS.INVOICES, initialInvoices);

    const savedUid = localStorage.getItem(STORAGE_KEYS.CURRENT_USER_ID);
    this.currentUserId = savedUid ? Number(savedUid) : 1; // Default to patient01 for instant preview
    this.token = localStorage.getItem(STORAGE_KEYS.TOKEN) || 'mock_jwt_token_patient01';
  }

  // --- Auth ---
  getCurrentUser(): { user: User; patient: Patient } | null {
    if (!this.currentUserId) return null;
    const user = this.users.find((u) => u.user_id === this.currentUserId);
    if (!user) return null;
    const patient = this.patients.find((p) => p.user_id === user.user_id) || {
      patient_id: user.user_id,
      user_id: user.user_id,
    };
    return { user, patient };
  }

  login(username: string, password: string): { user: User; patient: Patient; token: string } {
    const trimmedUsername = username.trim();
    const user = this.users.find(
      (u) => u.username.toLowerCase() === trimmedUsername.toLowerCase()
    );

    if (!user || user.password !== password) {
      throw new Error('Invalid username or password');
    }

    const patient = this.patients.find((p) => p.user_id === user.user_id) || {
      patient_id: user.user_id,
      user_id: user.user_id,
    };

    const token = `jwt_token_${user.username}_${Date.now()}`;
    this.currentUserId = user.user_id;
    this.token = token;

    localStorage.setItem(STORAGE_KEYS.CURRENT_USER_ID, String(user.user_id));
    localStorage.setItem(STORAGE_KEYS.TOKEN, token);

    return { user, patient, token };
  }

  register(data: {
    username: string;
    password: string;
    confirmPassword: string;
    full_name: string;
    phone?: string;
    email?: string;
    date_of_birth?: string;
    gender?: string;
    address?: string;
  }): { user: User; patient: Patient } {
    if (!data.username.trim()) throw new Error('Username is required');
    if (data.password.length < 8) throw new Error('Password must be at least 8 characters');
    if (data.password !== data.confirmPassword) throw new Error('Passwords do not match');
    if (!data.full_name.trim()) throw new Error('Full name is required');

    const existing = this.users.find(
      (u) => u.username.toLowerCase() === data.username.trim().toLowerCase()
    );
    if (existing) {
      throw new Error('Username is already taken');
    }

    const newUserId = Math.max(...this.users.map((u) => u.user_id), 0) + 1;
    const newPatientId = Math.max(...this.patients.map((p) => p.patient_id), 0) + 1;

    const newUser: User = {
      user_id: newUserId,
      username: data.username.trim(),
      full_name: data.full_name.trim(),
      phone: data.phone?.trim() || null,
      email: data.email?.trim() || null,
      role: 'PATIENT',
      is_active: true,
      password: data.password,
    };

    const newPatient: Patient = {
      patient_id: newPatientId,
      user_id: newUserId,
      date_of_birth: data.date_of_birth || null,
      gender: data.gender || 'MALE',
      address: data.address?.trim() || null,
    };

    this.users.push(newUser);
    this.patients.push(newPatient);

    save(STORAGE_KEYS.USERS, this.users);
    save(STORAGE_KEYS.PATIENTS, this.patients);

    return { user: newUser, patient: newPatient };
  }

  logout(): void {
    this.currentUserId = null;
    this.token = null;
    localStorage.removeItem(STORAGE_KEYS.CURRENT_USER_ID);
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
  }

  switchDemoUser(username: 'patient01' | 'patient02'): void {
    const user = this.users.find((u) => u.username === username);
    if (user) {
      this.currentUserId = user.user_id;
      this.token = `mock_jwt_token_${user.username}`;
      localStorage.setItem(STORAGE_KEYS.CURRENT_USER_ID, String(user.user_id));
      localStorage.setItem(STORAGE_KEYS.TOKEN, this.token);
    }
  }

  // --- Profile ---
  updateProfile(data: {
    full_name: string;
    phone?: string | null;
    email?: string | null;
    date_of_birth?: string | null;
    gender?: string | null;
    address?: string | null;
  }): { user: User; patient: Patient } {
    const current = this.getCurrentUser();
    if (!current) throw new Error('Not authenticated');

    // Update user
    const uIdx = this.users.findIndex((u) => u.user_id === current.user.user_id);
    if (uIdx !== -1) {
      this.users[uIdx] = {
        ...this.users[uIdx],
        full_name: data.full_name.trim(),
        phone: data.phone?.trim() || null,
        email: data.email?.trim() || null,
      };
      save(STORAGE_KEYS.USERS, this.users);
    }

    // Update patient
    const pIdx = this.patients.findIndex((p) => p.patient_id === current.patient.patient_id);
    if (pIdx !== -1) {
      this.patients[pIdx] = {
        ...this.patients[pIdx],
        date_of_birth: data.date_of_birth || null,
        gender: data.gender || null,
        address: data.address?.trim() || null,
      };
      save(STORAGE_KEYS.PATIENTS, this.patients);
    }

    return this.getCurrentUser()!;
  }

  // --- Appointments ---
  getMyAppointments(options: {
    page?: number;
    pageSize?: number;
    keyword?: string;
    status?: AppointmentStatus | 'ALL';
  } = {}): PageResponse<Appointment> {
    const current = this.getCurrentUser();
    if (!current) {
      return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    }

    const { page = 1, pageSize = 10, keyword = '', status = 'ALL' } = options;

    let list = this.appointments.filter((a) => a.patient_id === current.patient.patient_id);

    if (status && status !== 'ALL') {
      list = list.filter((a) => a.status === status);
    }

    if (keyword.trim()) {
      const q = keyword.toLowerCase().trim();
      list = list.filter(
        (a) =>
          a.doctor.full_name.toLowerCase().includes(q) ||
          a.doctor.specialty.toLowerCase().includes(q) ||
          a.clinic.clinic_name.toLowerCase().includes(q) ||
          a.reason.toLowerCase().includes(q)
      );
    }

    // Sort: newest appointment_date descending
    list.sort((a, b) => {
      const dateA = new Date(`${a.appointment_date}T${a.start_time}`);
      const dateB = new Date(`${b.appointment_date}T${b.start_time}`);
      return dateB.getTime() - dateA.getTime();
    });

    const total = list.length;
    const total_pages = Math.ceil(total / pageSize) || 1;
    const start = (page - 1) * pageSize;
    const items = list.slice(start, start + pageSize);

    return {
      items,
      total,
      page,
      page_size: pageSize,
      total_pages,
    };
  }

  getUpcomingAppointment(): Appointment | null {
    const current = this.getCurrentUser();
    if (!current) return null;

    const todayStr = new Date().toISOString().split('T')[0];
    const validStatuses: AppointmentStatus[] = ['CONFIRMED', 'PENDING', 'CHECKED_IN'];

    const upcoming = this.appointments
      .filter(
        (a) =>
          a.patient_id === current.patient.patient_id &&
          validStatuses.includes(a.status) &&
          a.appointment_date >= todayStr
      )
      .sort((a, b) => {
        const dateA = new Date(`${a.appointment_date}T${a.start_time}`).getTime();
        const dateB = new Date(`${b.appointment_date}T${b.start_time}`).getTime();
        return dateA - dateB;
      });

    return upcoming[0] || null;
  }

  getAppointmentDetail(appointmentId: number): Appointment | null {
    const current = this.getCurrentUser();
    if (!current) return null;

    const appt = this.appointments.find((a) => a.appointment_id === appointmentId);
    if (!appt || appt.patient_id !== current.patient.patient_id) return null;

    // Attach medical_record_id and invoice_id if found
    const record = this.medicalRecords.find((r) => r.appointment_id === appointmentId);
    const invoice = this.invoices.find((i) => i.appointment_id === appointmentId);

    return {
      ...appt,
      medical_record_id: record ? record.medical_record_id : appt.medical_record_id,
      invoice_id: invoice ? invoice.invoice_id : appt.invoice_id,
    };
  }

  // --- Medical Records ---
  getMyMedicalRecords(options: {
    page?: number;
    pageSize?: number;
    keyword?: string;
  } = {}): PageResponse<MedicalRecord> {
    const current = this.getCurrentUser();
    if (!current) {
      return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    }

    const { page = 1, pageSize = 10, keyword = '' } = options;

    let list = this.medicalRecords.filter((r) => r.patient_id === current.patient.patient_id);

    if (keyword.trim()) {
      const q = keyword.toLowerCase().trim();
      list = list.filter(
        (r) =>
          r.doctor.full_name.toLowerCase().includes(q) ||
          r.doctor.specialty.toLowerCase().includes(q) ||
          r.diagnosis.toLowerCase().includes(q) ||
          r.symptoms.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => new Date(b.examination_date).getTime() - new Date(a.examination_date).getTime());

    const total = list.length;
    const total_pages = Math.ceil(total / pageSize) || 1;
    const start = (page - 1) * pageSize;
    const items = list.slice(start, start + pageSize);

    return {
      items,
      total,
      page,
      page_size: pageSize,
      total_pages,
    };
  }

  getMedicalRecordDetail(recordId: number): MedicalRecord | null {
    const current = this.getCurrentUser();
    if (!current) return null;

    const record = this.medicalRecords.find((r) => r.medical_record_id === recordId);
    if (!record || record.patient_id !== current.patient.patient_id) return null;

    return record;
  }

  // --- Invoices ---
  getMyInvoices(options: {
    page?: number;
    pageSize?: number;
    status?: InvoiceStatus | 'ALL';
  } = {}): PageResponse<Invoice> {
    const current = this.getCurrentUser();
    if (!current) {
      return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 };
    }

    const { page = 1, pageSize = 10, status = 'ALL' } = options;

    let list = this.invoices.filter((i) => i.patient_id === current.patient.patient_id);

    if (status && status !== 'ALL') {
      list = list.filter((i) => i.status === status);
    }

    list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const total = list.length;
    const total_pages = Math.ceil(total / pageSize) || 1;
    const start = (page - 1) * pageSize;
    const items = list.slice(start, start + pageSize);

    return {
      items,
      total,
      page,
      page_size: pageSize,
      total_pages,
    };
  }

  getInvoiceDetail(invoiceId: number): Invoice | null {
    const current = this.getCurrentUser();
    if (!current) return null;

    const invoice = this.invoices.find((i) => i.invoice_id === invoiceId);
    if (!invoice || invoice.patient_id !== current.patient.patient_id) return null;

    return invoice;
  }

  payInvoice(invoiceId: number, paymentMethod: PaymentMethod = 'CARD'): Invoice {
    const current = this.getCurrentUser();
    if (!current) throw new Error('Not authenticated');

    const idx = this.invoices.findIndex((i) => i.invoice_id === invoiceId);
    if (idx === -1 || this.invoices[idx].patient_id !== current.patient.patient_id) {
      throw new Error('Invoice not found or unauthorized');
    }

    const inv = this.invoices[idx];
    if (inv.status === 'PAID') {
      return inv;
    }

    const payment = {
      payment_id: Date.now(),
      invoice_id: inv.invoice_id,
      amount: inv.total_amount,
      payment_method: paymentMethod,
      payment_date: new Date().toISOString(),
    };

    const updated: Invoice = {
      ...inv,
      status: 'PAID',
      payment,
    };

    this.invoices[idx] = updated;
    save(STORAGE_KEYS.INVOICES, this.invoices);
    return updated;
  }

  // --- Dashboard ---
  getDashboard(): DashboardData {
    const current = this.getCurrentUser();
    if (!current) {
      return {
        patient_name: 'Patient',
        total_appointments: 0,
        total_medical_records: 0,
        total_invoices: 0,
        unpaid_invoices: 0,
        upcoming_appointment: null,
      };
    }

    const pId = current.patient.patient_id;
    const total_appointments = this.appointments.filter((a) => a.patient_id === pId).length;
    const total_medical_records = this.medicalRecords.filter((r) => r.patient_id === pId).length;
    const patientInvoices = this.invoices.filter((i) => i.patient_id === pId);
    const total_invoices = patientInvoices.length;
    const unpaid_invoices = patientInvoices.filter((i) => i.status === 'UNPAID').length;
    const upcoming_appointment = this.getUpcomingAppointment();

    return {
      patient_name: current.user.full_name,
      total_appointments,
      total_medical_records,
      total_invoices,
      unpaid_invoices,
      upcoming_appointment,
    };
  }

  // ==========================================
  // --- RECEPTIONIST & STAFF MANAGEMENT API ---
  // ==========================================

  getReceptionDashboard(): ReceptionDashboardData {
    const todayStr = new Date().toISOString().split('T')[0];
    const todayAppts = this.appointments.filter((a) => a.appointment_date === todayStr);

    const today_total = todayAppts.length;
    const today_pending = todayAppts.filter((a) => a.status === 'PENDING').length;
    const today_confirmed = todayAppts.filter((a) => a.status === 'CONFIRMED').length;
    const today_checked_in = todayAppts.filter((a) => a.status === 'CHECKED_IN').length;
    const today_completed = todayAppts.filter((a) => a.status === 'COMPLETED').length;

    const unpaidInvoices = this.invoices.filter((i) => i.status === 'UNPAID');
    const unpaid_invoices_count = unpaidInvoices.length;
    const unpaid_invoices_amount = unpaidInvoices.reduce((sum, i) => sum + i.total_amount, 0);

    // Collected today
    const paidToday = this.invoices.filter((i) => {
      if (i.status !== 'PAID' || !i.payment) return false;
      const pDate = i.payment.payment_date.split('T')[0];
      return pDate === todayStr;
    });
    const today_revenue = paidToday.reduce((sum, i) => sum + i.total_amount, 0);

    // Recent queue of checked-in patients
    const checkedInAppts = this.appointments
      .filter((a) => a.status === 'CHECKED_IN')
      .map((a) => this._enrichAppointment(a))
      .slice(0, 5);

    return {
      today_total,
      today_pending,
      today_confirmed,
      today_checked_in,
      today_completed,
      unpaid_invoices_count,
      unpaid_invoices_amount,
      today_revenue,
      recent_queue: checkedInAppts,
    };
  }

  private _enrichAppointment(a: Appointment): ReceptionAppointment {
    const patient = this.patients.find((p) => p.patient_id === a.patient_id);
    const user = patient ? this.users.find((u) => u.user_id === patient.user_id) : null;
    return {
      ...a,
      patient_name: user?.full_name || `Patient #${a.patient_id}`,
      patient_phone: user?.phone || '',
      patient_gender: patient?.gender || '',
      patient_dob: patient?.date_of_birth || '',
    };
  }

  getReceptionAppointments(params: {
    page?: number;
    pageSize?: number;
    status?: string;
    keyword?: string;
    date?: string;
  }): PageResponse<ReceptionAppointment> {
    const page = params.page || 1;
    const pageSize = params.pageSize || 15;

    let list = this.appointments.map((a) => this._enrichAppointment(a));

    if (params.status && params.status !== 'ALL') {
      list = list.filter((a) => a.status === params.status);
    }
    if (params.date) {
      list = list.filter((a) => a.appointment_date === params.date);
    }
    if (params.keyword && params.keyword.trim()) {
      const q = params.keyword.toLowerCase().trim();
      list = list.filter(
        (a) =>
          a.patient_name.toLowerCase().includes(q) ||
          a.patient_phone.includes(q) ||
          a.reason.toLowerCase().includes(q) ||
          a.doctor.full_name.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      const dtA = `${a.appointment_date}T${a.start_time}`;
      const dtB = `${b.appointment_date}T${b.start_time}`;
      return dtB.localeCompare(dtA);
    });

    const total = list.length;
    const total_pages = Math.max(1, Math.ceil(total / pageSize));
    const start = (page - 1) * pageSize;
    const items = list.slice(start, start + pageSize);

    return { items, total, page, page_size: pageSize, total_pages };
  }

  confirmAppointmentStaff(appointmentId: number): ReceptionAppointment {
    const idx = this.appointments.findIndex((a) => a.appointment_id === appointmentId);
    if (idx === -1) throw new Error('Appointment not found');
    this.appointments[idx] = {
      ...this.appointments[idx],
      status: 'CONFIRMED',
    };
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    return this._enrichAppointment(this.appointments[idx]);
  }

  checkInPatientStaff(appointmentId: number, queueNumber?: string, notes?: string): ReceptionAppointment {
    const idx = this.appointments.findIndex((a) => a.appointment_id === appointmentId);
    if (idx === -1) throw new Error('Appointment not found');
    const existing = this.appointments[idx];
    const newReason = notes ? `${existing.reason} [Check-in note: ${notes}]` : existing.reason;

    this.appointments[idx] = {
      ...existing,
      status: 'CHECKED_IN',
      reason: newReason,
    };
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    return this._enrichAppointment(this.appointments[idx]);
  }

  cancelAppointmentStaff(appointmentId: number, reason: string): ReceptionAppointment {
    const idx = this.appointments.findIndex((a) => a.appointment_id === appointmentId);
    if (idx === -1) throw new Error('Appointment not found');
    const existing = this.appointments[idx];
    this.appointments[idx] = {
      ...existing,
      status: 'CANCELLED',
      reason: `${existing.reason} [Cancelled: ${reason}]`,
    };
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    return this._enrichAppointment(this.appointments[idx]);
  }

  rescheduleAppointmentStaff(
    appointmentId: number,
    newDate: string,
    newTime: string,
    reason?: string
  ): ReceptionAppointment {
    const idx = this.appointments.findIndex((a) => a.appointment_id === appointmentId);
    if (idx === -1) throw new Error('Appointment not found');
    const existing = this.appointments[idx];
    this.appointments[idx] = {
      ...existing,
      appointment_date: newDate,
      start_time: newTime,
      status: 'CONFIRMED',
      reason: reason || existing.reason,
    };
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    return this._enrichAppointment(this.appointments[idx]);
  }

  bookForPatient(data: {
    patient_id?: number;
    full_name: string;
    phone: string;
    date_of_birth?: string;
    gender?: string;
    address?: string;
    doctor_id: number;
    appointment_date: string;
    start_time: string;
    end_time: string;
    reason: string;
    auto_confirm?: boolean;
  }): ReceptionAppointment {
    let patientId = data.patient_id;

    if (!patientId) {
      // Find or create user
      let user = this.users.find((u) => u.phone === data.phone);
      if (!user) {
        const newUid = Math.max(...this.users.map((u) => u.user_id), 0) + 1;
        user = {
          user_id: newUid,
          username: `pt_${data.phone.slice(-6)}`,
          full_name: data.full_name,
          phone: data.phone,
          role: 'PATIENT',
          is_active: true,
        };
        this.users.push(user);
        save(STORAGE_KEYS.USERS, this.users);
      }

      let patient = this.patients.find((p) => p.user_id === user!.user_id);
      if (!patient) {
        const newPid = Math.max(...this.patients.map((p) => p.patient_id), 0) + 1;
        patient = {
          patient_id: newPid,
          user_id: user.user_id,
          gender: data.gender || 'OTHER',
          date_of_birth: data.date_of_birth || '',
          address: data.address || '',
        };
        this.patients.push(patient);
        save(STORAGE_KEYS.PATIENTS, this.patients);
      }
      patientId = patient.patient_id;
    }

    const newApptId = Math.max(...this.appointments.map((a) => a.appointment_id), 0) + 1;
    const status: AppointmentStatus = data.auto_confirm ? 'CONFIRMED' : 'PENDING';

    const newAppt: Appointment = {
      appointment_id: newApptId,
      patient_id: patientId,
      doctor_id: data.doctor_id,
      clinic_id: 1,
      appointment_date: data.appointment_date,
      start_time: data.start_time,
      end_time: data.end_time,
      reason: data.reason,
      status,
      created_at: new Date().toISOString(),
      doctor: {
        doctor_id: data.doctor_id,
        full_name: data.doctor_id === 2 ? 'Dr. Tran Van Duc' : data.doctor_id === 3 ? 'Dr. Pham Minh Tri' : 'Dr. Le Thi Mai',
        specialty: data.doctor_id === 2 ? 'Cardiology' : data.doctor_id === 3 ? 'Pediatrics' : 'Internal Medicine',
      },
      clinic: {
        clinic_id: 1,
        clinic_name: 'ClinicCare Central',
        address: '123 Nguyen Hue Blvd, District 1, HCMC',
        phone: '028 3822 1234',
      },
    };

    this.appointments.unshift(newAppt);
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    return this._enrichAppointment(newAppt);
  }

  getReceptionInvoices(params: {
    page?: number;
    pageSize?: number;
    status?: string;
    keyword?: string;
  }): PageResponse<Invoice & { patient_name: string; patient_phone: string }> {
    const page = params.page || 1;
    const pageSize = params.pageSize || 15;

    let list = this.invoices.map((inv) => {
      const patient = this.patients.find((p) => p.patient_id === inv.patient_id);
      const user = patient ? this.users.find((u) => u.user_id === patient.user_id) : null;
      return {
        ...inv,
        patient_name: user?.full_name || `Patient #${inv.patient_id}`,
        patient_phone: user?.phone || '',
      };
    });

    if (params.status && params.status !== 'ALL') {
      list = list.filter((i) => i.status === params.status);
    }
    if (params.keyword && params.keyword.trim()) {
      const q = params.keyword.toLowerCase().trim();
      list = list.filter(
        (i) =>
          i.patient_name.toLowerCase().includes(q) ||
          i.patient_phone.includes(q) ||
          i.appointment.doctor.full_name.toLowerCase().includes(q) ||
          String(i.invoice_id).includes(q)
      );
    }

    list.sort((a, b) => b.invoice_id - a.invoice_id);

    const total = list.length;
    const total_pages = Math.max(1, Math.ceil(total / pageSize));
    const start = (page - 1) * pageSize;
    const items = list.slice(start, start + pageSize);

    return { items, total, page, page_size: pageSize, total_pages };
  }

  createInvoiceStaff(
    appointmentId: number,
    items: Array<{ item_name: string; quantity: number; unit_price: number }>
  ): Invoice {
    const appt = this.appointments.find((a) => a.appointment_id === appointmentId);
    if (!appt) throw new Error('Appointment not found');

    const total_amount = items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
    const newInvoiceId = Math.max(...this.invoices.map((i) => i.invoice_id), 0) + 1;

    const invoiceItems: InvoiceItem[] = items.map((it, idx) => ({
      item_id: Date.now() + idx,
      item_name: it.item_name,
      quantity: it.quantity,
      unit_price: it.unit_price,
      line_total: it.unit_price * it.quantity,
    }));

    const newInvoice: Invoice = {
      invoice_id: newInvoiceId,
      appointment_id: appointmentId,
      patient_id: appt.patient_id,
      created_at: new Date().toISOString(),
      total_amount,
      status: 'UNPAID',
      appointment: {
        appointment_date: appt.appointment_date,
        start_time: appt.start_time,
        doctor: {
          doctor_id: appt.doctor.doctor_id,
          full_name: appt.doctor.full_name,
        },
      },
      items: invoiceItems,
      payment: null,
    };

    this.invoices.unshift(newInvoice);
    save(STORAGE_KEYS.INVOICES, this.invoices);

    // Update appointment status to COMPLETED
    const aIdx = this.appointments.findIndex((a) => a.appointment_id === appointmentId);
    if (aIdx !== -1) {
      this.appointments[aIdx] = {
        ...this.appointments[aIdx],
        status: 'COMPLETED',
        invoice_id: newInvoiceId,
      };
      save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    }

    return newInvoice;
  }

  payInvoiceStaff(invoiceId: number, paymentMethod: PaymentMethod | string): Invoice {
    const idx = this.invoices.findIndex((i) => i.invoice_id === invoiceId);
    if (idx === -1) throw new Error('Invoice not found');

    const inv = this.invoices[idx];
    if (inv.status === 'PAID') return inv;

    const payment = {
      payment_id: Date.now(),
      invoice_id: inv.invoice_id,
      amount: inv.total_amount,
      payment_method: paymentMethod as PaymentMethod,
      payment_date: new Date().toISOString(),
    };

    const updated: Invoice = {
      ...inv,
      status: 'PAID',
      payment,
    };

    this.invoices[idx] = updated;
    save(STORAGE_KEYS.INVOICES, this.invoices);
    return updated;
  }

  getPaymentHistory(params: {
    page?: number;
    pageSize?: number;
    paymentMethod?: string;
    keyword?: string;
  }): PageResponse<PaymentRecord> {
    const page = params.page || 1;
    const pageSize = params.pageSize || 15;

    const records: PaymentRecord[] = [];
    for (const inv of this.invoices) {
      if (inv.status === 'PAID' && inv.payment) {
        const patient = this.patients.find((p) => p.patient_id === inv.patient_id);
        const user = patient ? this.users.find((u) => u.user_id === patient.user_id) : null;
        records.push({
          payment_id: inv.payment.payment_id,
          invoice_id: inv.invoice_id,
          amount: inv.payment.amount,
          payment_method: inv.payment.payment_method,
          payment_date: inv.payment.payment_date,
          patient_name: user?.full_name || `Patient #${inv.patient_id}`,
          doctor_name: inv.appointment.doctor.full_name,
          total_amount: inv.total_amount,
        });
      }
    }

    let filtered = records;
    if (params.paymentMethod && params.paymentMethod !== 'ALL') {
      filtered = filtered.filter((p) => p.payment_method === params.paymentMethod);
    }
    if (params.keyword && params.keyword.trim()) {
      const q = params.keyword.toLowerCase().trim();
      filtered = filtered.filter(
        (p) =>
          p.patient_name.toLowerCase().includes(q) ||
          p.doctor_name.toLowerCase().includes(q) ||
          String(p.invoice_id).includes(q)
      );
    }

    filtered.sort((a, b) => b.payment_date.localeCompare(a.payment_date));

    const total = filtered.length;
    const total_pages = Math.max(1, Math.ceil(total / pageSize));
    const start = (page - 1) * pageSize;
    const items = filtered.slice(start, start + pageSize);

    return { items, total, page, page_size: pageSize, total_pages };
  }

  searchPatients(query: string): Array<{
    patient_id: number;
    full_name: string;
    phone: string;
    gender: string;
    date_of_birth: string;
  }> {
    if (!query || query.trim().length < 2) return [];
    const q = query.toLowerCase().trim();

    return this.patients
      .map((p) => {
        const u = this.users.find((user) => user.user_id === p.user_id);
        return {
          patient_id: p.patient_id,
          full_name: u?.full_name || '',
          phone: u?.phone || '',
          gender: p.gender || 'OTHER',
          date_of_birth: p.date_of_birth || '',
        };
      })
      .filter((p) => p.full_name.toLowerCase().includes(q) || p.phone.includes(q))
      .slice(0, 8);
  }


  // Reset to original seed
  resetData(): void {
    localStorage.removeItem(STORAGE_KEYS.USERS);
    localStorage.removeItem(STORAGE_KEYS.PATIENTS);
    localStorage.removeItem(STORAGE_KEYS.APPOINTMENTS);
    localStorage.removeItem(STORAGE_KEYS.MEDICAL_RECORDS);
    localStorage.removeItem(STORAGE_KEYS.INVOICES);

    this.users = [...initialUsers];
    this.patients = [...initialPatients];
    this.appointments = [...initialAppointments];
    this.medicalRecords = [...initialMedicalRecords];
    this.invoices = [...initialInvoices];
    this.currentUserId = 1;
    this.token = 'mock_jwt_token_patient01';

    save(STORAGE_KEYS.USERS, this.users);
    save(STORAGE_KEYS.PATIENTS, this.patients);
    save(STORAGE_KEYS.APPOINTMENTS, this.appointments);
    save(STORAGE_KEYS.MEDICAL_RECORDS, this.medicalRecords);
    save(STORAGE_KEYS.INVOICES, this.invoices);
    localStorage.setItem(STORAGE_KEYS.CURRENT_USER_ID, '1');
    localStorage.setItem(STORAGE_KEYS.TOKEN, this.token);
  }
}

export const storageService = new ClinicStorageService();
