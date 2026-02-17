-- Migration 012
-- Adds tags to targets.

CREATE TABLE IF NOT EXISTS tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS target_tags (
    target_id CHAR(36) NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY(target_id, tag_id),
    FOREIGN KEY(target_id) REFERENCES targets(id) ON DELETE CASCADE,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

INSERT INTO schema_versions (version, description) VALUES (12, 'Add tags')
