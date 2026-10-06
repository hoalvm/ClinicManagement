-- Preserve audit history even if the application SQL identity is accidentally
-- granted UPDATE or DELETE. DBA-controlled retention must explicitly disable
-- this trigger during an approved archival operation.
CREATE OR ALTER TRIGGER dbo.TR_AuditEvents_AppendOnly
ON dbo.AuditEvents
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    THROW 51000, 'AuditEvents is append-only.', 1;
END;
GO
