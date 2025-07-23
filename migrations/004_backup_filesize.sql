-- Migration 004
-- Adds a filesize field for backups. Set to 0 for every existing backup.

ALTER TABLE backups ADD COLUMN filesize INTEGER NOT NULL DEFAULT 0 AFTER is_recycled
