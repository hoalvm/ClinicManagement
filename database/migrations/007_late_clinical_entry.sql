-- Preserve the reason when a clinician completes an in-progress visit after
-- its scheduled date. Older records remain NULL and are not reclassified.
IF COL_LENGTH('dbo.MedicalRecords', 'LateEntryReason') IS NULL
    ALTER TABLE dbo.MedicalRecords ADD LateEntryReason NVARCHAR(500) NULL;
GO
