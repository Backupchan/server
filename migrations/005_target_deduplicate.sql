-- Migration 005
-- Adds a deduplicate boolean column to targets.

ALTER TABLE targets ADD COLUMN deduplicate INTEGER NOT NULL CHECK (deduplicate IN (0, 1)) AFTER name_template
