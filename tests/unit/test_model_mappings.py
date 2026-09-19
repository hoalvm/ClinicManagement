"""Schema-contract checks that do not connect to or recreate a database."""

from sqlalchemy import Boolean, Date, Integer, Numeric, Time
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, TINYINT

from backend.app.models import Base

EXPECTED_COLUMNS = {
    "Users": {
        "UserID",
        "Username",
        "PasswordHash",
        "FullName",
        "Phone",
        "Email",
        "Role",
        "IsActive",
        "CreatedAt",
    },
    "Patients": {"PatientID", "UserID", "DateOfBirth", "Gender", "Address"},
    "Specialties": {"SpecialtyID", "SpecialtyName", "Description", "IsActive"},
    "Clinics": {"ClinicID", "ClinicName", "Address", "Phone", "IsActive"},
    "Doctors": {
        "DoctorID",
        "UserID",
        "SpecialtyID",
        "ClinicID",
        "LicenseNumber",
        "IsActive",
    },
    "DoctorSchedules": {
        "ScheduleID",
        "DoctorID",
        "DayOfWeek",
        "StartTime",
        "EndTime",
        "SlotDuration",
        "IsActive",
    },
    "Appointments": {
        "AppointmentID",
        "PatientID",
        "DoctorID",
        "ClinicID",
        "AppointmentDate",
        "StartTime",
        "EndTime",
        "Reason",
        "Status",
        "CreatedAt",
    },
    "MedicalRecords": {
        "MedicalRecordID",
        "AppointmentID",
        "Symptoms",
        "Diagnosis",
        "Notes",
        "ExaminationDate",
    },
    "Prescriptions": {"PrescriptionID", "MedicalRecordID", "CreatedAt"},
    "PrescriptionItems": {
        "PrescriptionItemID",
        "PrescriptionID",
        "MedicineName",
        "Quantity",
        "Dosage",
        "Instructions",
    },
    "Invoices": {"InvoiceID", "AppointmentID", "TotalAmount", "Status", "CreatedAt"},
    "InvoiceItems": {"InvoiceItemID", "InvoiceID", "ItemName", "Quantity", "UnitPrice"},
    "Payments": {"PaymentID", "InvoiceID", "Amount", "PaymentMethod", "PaymentDate"},
}


def test_all_source_of_truth_tables_are_mapped_exactly() -> None:
    actual_tables = set(Base.metadata.tables)

    assert actual_tables == set(EXPECTED_COLUMNS)
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        actual_columns = {column.name for column in Base.metadata.tables[table_name].columns}
        assert actual_columns == expected_columns, table_name


def test_application_models_do_not_define_surrogate_schema_fields() -> None:
    forbidden_columns = {
        "Patients": {"FullName", "Email", "Phone"},
        "Doctors": {"FullName", "Email", "Phone", "Specialty"},
        "Appointments": {"AppointmentDateTime", "DoctorName"},
        "MedicalRecords": {
            "PatientID",
            "DoctorID",
            "Treatment",
            "Prescription",
            "ResultSummary",
            "DoctorNotes",
        },
        "Invoices": {"PatientID", "InvoiceCode", "PaymentMethod", "Notes"},
    }

    for table_name, disallowed in forbidden_columns.items():
        actual_columns = {column.name for column in Base.metadata.tables[table_name].columns}
        assert actual_columns.isdisjoint(disallowed), table_name


EXPECTED_TYPE_SIGNATURES = {
    "Users": {
        "UserID": (Integer,),
        "Username": (NVARCHAR, 50),
        "PasswordHash": (NVARCHAR, 255),
        "FullName": (NVARCHAR, 100),
        "Phone": (NVARCHAR, 15),
        "Email": (NVARCHAR, 100),
        "Role": (NVARCHAR, 20),
        "IsActive": (Boolean,),
        "CreatedAt": (DATETIME2,),
    },
    "Patients": {
        "PatientID": (Integer,),
        "UserID": (Integer,),
        "DateOfBirth": (Date,),
        "Gender": (NVARCHAR, 10),
        "Address": (NVARCHAR, 255),
    },
    "Specialties": {
        "SpecialtyID": (Integer,),
        "SpecialtyName": (NVARCHAR, 100),
        "Description": (NVARCHAR, 255),
        "IsActive": (Boolean,),
    },
    "Clinics": {
        "ClinicID": (Integer,),
        "ClinicName": (NVARCHAR, 150),
        "Address": (NVARCHAR, 255),
        "Phone": (NVARCHAR, 15),
        "IsActive": (Boolean,),
    },
    "Doctors": {
        "DoctorID": (Integer,),
        "UserID": (Integer,),
        "SpecialtyID": (Integer,),
        "ClinicID": (Integer,),
        "LicenseNumber": (NVARCHAR, 50),
        "IsActive": (Boolean,),
    },
    "DoctorSchedules": {
        "ScheduleID": (Integer,),
        "DoctorID": (Integer,),
        "DayOfWeek": (TINYINT,),
        "StartTime": (Time,),
        "EndTime": (Time,),
        "SlotDuration": (Integer,),
        "IsActive": (Boolean,),
    },
    "Appointments": {
        "AppointmentID": (Integer,),
        "PatientID": (Integer,),
        "DoctorID": (Integer,),
        "ClinicID": (Integer,),
        "AppointmentDate": (Date,),
        "StartTime": (Time,),
        "EndTime": (Time,),
        "Reason": (NVARCHAR, 500),
        "Status": (NVARCHAR, 20),
        "CreatedAt": (DATETIME2,),
    },
    "MedicalRecords": {
        "MedicalRecordID": (Integer,),
        "AppointmentID": (Integer,),
        "Symptoms": (NVARCHAR, 1000),
        "Diagnosis": (NVARCHAR, 1000),
        "Notes": (NVARCHAR, 2000),
        "ExaminationDate": (DATETIME2,),
    },
    "Prescriptions": {
        "PrescriptionID": (Integer,),
        "MedicalRecordID": (Integer,),
        "CreatedAt": (DATETIME2,),
    },
    "PrescriptionItems": {
        "PrescriptionItemID": (Integer,),
        "PrescriptionID": (Integer,),
        "MedicineName": (NVARCHAR, 150),
        "Quantity": (Integer,),
        "Dosage": (NVARCHAR, 255),
        "Instructions": (NVARCHAR, 500),
    },
    "Invoices": {
        "InvoiceID": (Integer,),
        "AppointmentID": (Integer,),
        "TotalAmount": (Numeric, 18, 2),
        "Status": (NVARCHAR, 20),
        "CreatedAt": (DATETIME2,),
    },
    "InvoiceItems": {
        "InvoiceItemID": (Integer,),
        "InvoiceID": (Integer,),
        "ItemName": (NVARCHAR, 200),
        "Quantity": (Integer,),
        "UnitPrice": (Numeric, 18, 2),
    },
    "Payments": {
        "PaymentID": (Integer,),
        "InvoiceID": (Integer,),
        "Amount": (Numeric, 18, 2),
        "PaymentMethod": (NVARCHAR, 20),
        "PaymentDate": (DATETIME2,),
    },
}


def _type_signature(column_type: object) -> tuple[object, ...]:
    type_class = type(column_type)
    if type_class is NVARCHAR:
        return (type_class, column_type.length)
    if type_class is Numeric:
        return (type_class, column_type.precision, column_type.scale)
    return (type_class,)


def test_columns_keep_exact_sql_server_physical_types() -> None:
    actual = {
        table_name: {
            column.name: _type_signature(column.type)
            for column in Base.metadata.tables[table_name].columns
        }
        for table_name in EXPECTED_TYPE_SIGNATURES
    }

    assert actual == EXPECTED_TYPE_SIGNATURES


def test_nullable_columns_match_the_existing_database() -> None:
    expected_nullable = {
        "Users.Phone",
        "Users.Email",
        "Patients.DateOfBirth",
        "Patients.Gender",
        "Patients.Address",
        "Specialties.Description",
        "Clinics.Address",
        "Clinics.Phone",
        "Doctors.ClinicID",
        "Doctors.LicenseNumber",
        "Appointments.ClinicID",
        "Appointments.Reason",
        "MedicalRecords.Symptoms",
        "MedicalRecords.Diagnosis",
        "MedicalRecords.Notes",
        "PrescriptionItems.Dosage",
        "PrescriptionItems.Instructions",
    }
    actual_nullable = {
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.nullable
    }

    assert actual_nullable == expected_nullable


def test_unique_columns_match_one_to_one_database_relationships() -> None:
    expected_unique = {
        "Users.Username",
        "Patients.UserID",
        "Specialties.SpecialtyName",
        "Doctors.UserID",
        "Doctors.LicenseNumber",
        "MedicalRecords.AppointmentID",
        "Prescriptions.MedicalRecordID",
        "Invoices.AppointmentID",
        "Payments.InvoiceID",
    }
    actual_unique = {
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.unique
    }

    assert actual_unique == expected_unique


def test_foreign_keys_match_the_existing_database() -> None:
    expected_foreign_keys = {
        "Patients.UserID": "Users.UserID",
        "Doctors.UserID": "Users.UserID",
        "Doctors.SpecialtyID": "Specialties.SpecialtyID",
        "Doctors.ClinicID": "Clinics.ClinicID",
        "DoctorSchedules.DoctorID": "Doctors.DoctorID",
        "Appointments.PatientID": "Patients.PatientID",
        "Appointments.DoctorID": "Doctors.DoctorID",
        "Appointments.ClinicID": "Clinics.ClinicID",
        "MedicalRecords.AppointmentID": "Appointments.AppointmentID",
        "Prescriptions.MedicalRecordID": "MedicalRecords.MedicalRecordID",
        "PrescriptionItems.PrescriptionID": "Prescriptions.PrescriptionID",
        "Invoices.AppointmentID": "Appointments.AppointmentID",
        "InvoiceItems.InvoiceID": "Invoices.InvoiceID",
        "Payments.InvoiceID": "Invoices.InvoiceID",
    }
    actual_foreign_keys = {
        f"{table.name}.{column.name}": foreign_key.target_fullname
        for table in Base.metadata.tables.values()
        for column in table.columns
        for foreign_key in column.foreign_keys
    }

    assert actual_foreign_keys == expected_foreign_keys


def test_server_defaults_match_the_existing_database() -> None:
    expected_defaults = {
        "Users.IsActive": "1",
        "Users.CreatedAt": "GETDATE()",
        "Specialties.IsActive": "1",
        "Clinics.IsActive": "1",
        "Doctors.IsActive": "1",
        "DoctorSchedules.SlotDuration": "30",
        "DoctorSchedules.IsActive": "1",
        "Appointments.Status": "'PENDING'",
        "Appointments.CreatedAt": "GETDATE()",
        "MedicalRecords.ExaminationDate": "GETDATE()",
        "Prescriptions.CreatedAt": "GETDATE()",
        "Invoices.TotalAmount": "0",
        "Invoices.Status": "'UNPAID'",
        "Invoices.CreatedAt": "GETDATE()",
        "InvoiceItems.Quantity": "1",
        "Payments.PaymentDate": "GETDATE()",
    }
    actual_defaults = {
        f"{table.name}.{column.name}": str(column.server_default.arg)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.server_default is not None
    }

    assert actual_defaults == expected_defaults
