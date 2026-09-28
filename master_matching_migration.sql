-- Master Matching uses the existing master tables from 001_initial_schema.sql.
-- No new tables are required in V1. Decisions are recorded in verification_tasks.
-- Apply this only if the existing schema is already installed; it is intentionally idempotent.

CREATE INDEX IF NOT EXISTS idx_parts_part_number ON parts (part_number);
CREATE INDEX IF NOT EXISTS idx_equipment_models_model ON equipment_models (model);
CREATE INDEX IF NOT EXISTS idx_manufacturers_name ON manufacturers (name);
CREATE INDEX IF NOT EXISTS idx_verification_tasks_rfq_line ON verification_tasks (rfq_line_id, status);

CREATE TABLE IF NOT EXISTS part_applications (
    id BIGSERIAL PRIMARY KEY,
    part_id BIGINT NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    equipment_model_id BIGINT NOT NULL REFERENCES equipment_models(id) ON DELETE CASCADE,
    application_notes TEXT,
    source VARCHAR(500),
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_part_application UNIQUE (part_id, equipment_model_id)
);

CREATE TABLE IF NOT EXISTS part_relations (
    id BIGSERIAL PRIMARY KEY,
    part_id BIGINT NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    related_part_id BIGINT NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    relation_type VARCHAR(40) NOT NULL,
    source VARCHAR(500),
    notes TEXT,
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_part_relation_not_self CHECK (part_id <> related_part_id),
    CONSTRAINT uq_part_relation UNIQUE (part_id, related_part_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_part_applications_part ON part_applications(part_id);
CREATE INDEX IF NOT EXISTS idx_part_applications_equipment ON part_applications(equipment_model_id);
CREATE INDEX IF NOT EXISTS idx_part_relations_part ON part_relations(part_id);
CREATE INDEX IF NOT EXISTS idx_part_relations_related ON part_relations(related_part_id);
