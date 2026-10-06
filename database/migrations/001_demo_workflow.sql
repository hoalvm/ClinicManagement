-- Compatible with the original ClinicManagementDB.sql and with a fresh schema.
-- The migration runner records this file only after the transaction succeeds.
IF COL_LENGTH('dbo.Appointments', 'QueueNumber') IS NULL
    ALTER TABLE dbo.Appointments ADD QueueNumber NVARCHAR(10) NULL;
IF COL_LENGTH('dbo.Appointments', 'CheckInAt') IS NULL
    ALTER TABLE dbo.Appointments ADD CheckInAt DATETIME2 NULL;
IF COL_LENGTH('dbo.Appointments', 'CheckInNote') IS NULL
    ALTER TABLE dbo.Appointments ADD CheckInNote NVARCHAR(500) NULL;
IF COL_LENGTH('dbo.Appointments', 'CancellationReason') IS NULL
    ALTER TABLE dbo.Appointments ADD CancellationReason NVARCHAR(500) NULL;
IF COL_LENGTH('dbo.Appointments', 'LastRescheduleReason') IS NULL
    ALTER TABLE dbo.Appointments ADD LastRescheduleReason NVARCHAR(500) NULL;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.Appointments')
      AND name = 'UX_Appointments_ClinicDateQueue'
)
    CREATE UNIQUE INDEX UX_Appointments_ClinicDateQueue
        ON dbo.Appointments (ClinicID, AppointmentDate, QueueNumber)
        WHERE ClinicID IS NOT NULL AND QueueNumber IS NOT NULL;
GO

-- Existing CARD receipts remain readable; newly recorded payments use CASH or TRANSFER.
IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.Payments')
      AND name = 'CK_Payments_Method'
)
    ALTER TABLE dbo.Payments DROP CONSTRAINT CK_Payments_Method;
ALTER TABLE dbo.Payments ADD CONSTRAINT CK_Payments_Method
    CHECK (PaymentMethod IN ('CASH', 'CARD', 'TRANSFER'));
GO
