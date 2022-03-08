CREATE TABLE IF NOT EXISTS tags (
    name TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    uses BIGINT NOT NULL DEFAULT 0,
)

CREATE INDEX IF NOT EXISTS idx_name ON tags(name);
