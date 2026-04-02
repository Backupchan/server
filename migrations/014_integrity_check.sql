-- Migration 014
-- Adds columns for integrity checking on backups.

ALTER TABLE backups ADD COLUMN hash CHAR(64) DEFAULT NULL AFTER filesize;
ALTER TABLE backups ADD COLUMN hash_mismatch BOOLEAN NOT NULL DEFAULT FALSE AFTER hash;
