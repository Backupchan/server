-- Migration 008
-- Adds a schema versions table.

CREATE TABLE IF NOT EXISTS schema_versions (
    version INT NOT NULL,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_versions (version, description) VALUES (8, 'Add schema versions table')
