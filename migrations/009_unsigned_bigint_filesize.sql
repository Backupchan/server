-- Migration 009
-- Changes the filesize column in the backups table to be an UNSIGNED BIGINT--I mean, a BIGINT UNSIGNED.
-- (why does MySQL have to be so unintuitive!?)
-- This became necessary when I tried uploading a 6GB folder as a stress test.

ALTER TABLE backups MODIFY COLUMN filesize BIGINT UNSIGNED;
INSERT INTO schema_versions (version, description) VALUES (9, 'Change backups.filesize column to UNSIGNED BIGINT');
