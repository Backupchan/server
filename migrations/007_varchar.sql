-- Migration 007
-- Replace TEXT with VARCHAR for columns.

ALTER TABLE targets MODIFY COLUMN name VARCHAR(255);
ALTER TABLE targets MODIFY COLUMN type VARCHAR(6);
ALTER TABLE targets MODIFY COLUMN recycle_criteria VARCHAR(5);
ALTER TABLE targets MODIFY COLUMN recycle_action VARCHAR(7);
ALTER TABLE targets MODIFY COLUMN location VARCHAR(255);
ALTER TABLE targets MODIFY COLUMN name_template VARCHAR(255);
