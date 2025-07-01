-- Migration 003
-- This adds a is_recycled field to backups, for use with the recycle bin.

ALTER TABLE backups ADD COLUMN is_recycled BOOLEAN NOT NULL DEFAULT FALSE AFTER manual;
