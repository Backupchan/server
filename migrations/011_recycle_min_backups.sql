-- Migration 011
-- Adds a minimal backup count to keep to targets.

ALTER TABLE targets ADD COLUMN min_backups INTEGER NOT NULL DEFAULT 0 AFTER alias;
INSERT INTO schema_versions (version, description) VALUES (11, 'Add minimal backup count in targets')
