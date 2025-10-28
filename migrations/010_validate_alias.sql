-- Migration 010
-- Adds a check to the targets.alias column to make sure it doesn't look like a UUID.

ALTER TABLE targets ADD CONSTRAINT rcAliasUUID CHECK (alias NOT REGEXP '^[0-9a-fA-F-]{36}$');
INSERT INTO schema_versions (version, description) VALUES (10, 'Add a check to targets.alias to make sure it is not a UUID')
