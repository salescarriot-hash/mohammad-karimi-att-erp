CREATE TABLE IF NOT EXISTS knowledge_conflicts (
    id BIGSERIAL PRIMARY KEY,
    assertion_id BIGINT NOT NULL REFERENCES knowledge_assertions(id) ON DELETE CASCADE,
    existing_assertion_id BIGINT NOT NULL REFERENCES knowledge_assertions(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    current_value TEXT,
    new_value TEXT,
    status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    resolution TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_knowledge_conflict_not_self CHECK (assertion_id <> existing_assertion_id)
);
CREATE INDEX IF NOT EXISTS ix_knowledge_conflicts_status ON knowledge_conflicts(status);
CREATE INDEX IF NOT EXISTS ix_knowledge_conflicts_assertion ON knowledge_conflicts(assertion_id);
