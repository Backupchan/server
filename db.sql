CREATE TABLE targets (
    id TEXT PRIMARY KEY, -- Stored as a UUID
    name TEXT NOT NULL, -- Name of target set by user
    type TEXT NOT NULL CHECK (
        type IN (
            'single',
            'multi' -- ToHeart reference, I know.
        )
    ),

    -- Recycle-related fields
    recycle_criteria TEXT NOT NULL CHECK (
        recycle_criteria IN (
            'none', -- Do not recycle, keep all backups
            'count', -- Recycle after reached N copies
            'age' -- Recycle after copy is N days old
        )
    ),
    recycle_value INTEGER, -- the N in question
    recycle_action TEXT CHECK (
        recycle_action IN (
            'delete', -- Permanently delete backup
            'recycle' -- Put backup into recycle bin
        )
    ),

    location TEXT NOT NULL,
    name_template TEXT NOT NULL
);

CREATE TABLE backups (
    id TEXT PRIMARY KEY, -- UUID
    target_id TEXT NOT NULL,
    created_at TEXT NOT NULL, -- Assumed to be in ISO 8601. Please do not try to put anything else. SQLite does not know what a DATETIME is.
    manual INTEGER NOT NULL CHECK (manual IN (0, 1)), -- Boolean integer
    FOREIGN KEY (target_id) REFERENCES targets(id) ON DELETE CASCADE
);
