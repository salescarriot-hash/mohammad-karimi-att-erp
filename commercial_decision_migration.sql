CREATE TABLE IF NOT EXISTS commercial_decisions (
 id BIGSERIAL PRIMARY KEY,
 rfq_line_id BIGINT NOT NULL REFERENCES rfq_lines(id) ON DELETE CASCADE,
 selected_supplier_quote_line_id BIGINT REFERENCES supplier_quote_lines(id) ON DELETE SET NULL,
 decision_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
 target_purchase_price NUMERIC(20,6),
 target_currency VARCHAR(10),
 technical_status VARCHAR(50),
 commercial_notes TEXT,
 decided_by BIGINT,
 decided_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 CONSTRAINT chk_commercial_decision_status CHECK (decision_status IN ('PENDING','PROCEED','HOLD','REJECT'))
);
CREATE INDEX IF NOT EXISTS idx_commercial_decisions_line ON commercial_decisions(rfq_line_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_commercial_decisions_selected_quote ON commercial_decisions(selected_supplier_quote_line_id);
