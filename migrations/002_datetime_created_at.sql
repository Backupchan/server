-- Migration 002
-- This changes the type of the created_at field in the backups table to a DATETIME.
-- SQLite was in use before this, which does not support DATETIME fields.

-- Convert existing created_at fields to a temporary column
ALTER TABLE backups ADD COLUMN created_at_dt DATETIME AFTER target_id;
UPDATE backups SET created_at_dt = STR_TO_DATE(SUBSTRING_INDEX(created_at, '.', 1), '%Y-%m-%dT%H:%i:%s');

ALTER TABLE backups DROP COLUMN created_at;
ALTER TABLE backups CHANGE created_at_dt created_at DATETIME;
