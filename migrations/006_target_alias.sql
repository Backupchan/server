-- Migration 006
-- Adds an alias field to targets.

ALTER TABLE targets ADD COLUMN alias VARCHAR(255) NULL AFTER deduplicate;
ALTER TABLE targets ADD CONSTRAINT ucAlias UNIQUE (alias);