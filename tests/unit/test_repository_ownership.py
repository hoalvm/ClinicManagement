"""Compile ownership queries with SQL Server without opening a database."""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import mssql

from backend.app.repositories.appointment_repository import AppointmentRepository
from backend.app.repositories.invoice_repository import InvoiceRepository
from backend.app.repositories.medical_record_repository import MedicalRecordRepository


@pytest.mark.parametrize(
    ("repository_factory", "resource_id", "expected_from", "expected_predicate"),
    [
        (
            AppointmentRepository,
            7001,
            "FROM [Appointments]",
            "[Appointments].[AppointmentID] = 7001",
        ),
        (
            MedicalRecordRepository,
            7002,
            "FROM [MedicalRecords] JOIN [Appointments]",
            "[MedicalRecords].[MedicalRecordID] = 7002",
        ),
        (
            InvoiceRepository,
            7003,
            "FROM [Invoices] JOIN [Appointments]",
            "[Invoices].[InvoiceID] = 7003",
        ),
    ],
)
def test_get_owned_queries_include_current_patient_scope_for_sql_server(
    repository_factory: Callable[[Any], Any],
    resource_id: int,
    expected_from: str,
    expected_predicate: str,
) -> None:
    session = MagicMock(name="sql_server_session")
    session.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None
    repository = repository_factory(session)

    repository.get_owned(resource_id, 9001)

    statement = session.execute.call_args.args[0]
    sql = str(
        statement.compile(
            dialect=mssql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert expected_from in sql
    assert expected_predicate in sql
    assert "[Appointments].[PatientID] = 9001" in sql
