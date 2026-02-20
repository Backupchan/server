-- Migration 013
-- Adds constraints to tag names: no spaces or commas.

ALTER TABLE tags ADD CONSTRAINT rcTags CHECK (name NOT LIKE '%,%' AND name NOT LIKE '% %');
INSERT INTO schema_versions (version, description) VALUES (13, 'Add a check to target tag names')
