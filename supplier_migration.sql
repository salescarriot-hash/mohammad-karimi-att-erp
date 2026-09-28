CREATE TABLE IF NOT EXISTS suppliers (
 id BIGSERIAL PRIMARY KEY, name VARCHAR(255) NOT NULL, name_en VARCHAR(255), supplier_type VARCHAR(50),
 country VARCHAR(100), city VARCHAR(100), website VARCHAR(500), contact_name VARCHAR(255), email VARCHAR(255),
 phone VARCHAR(100), whatsapp VARCHAR(100), address TEXT, notes TEXT, status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
 verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS supplier_quotes (
 id BIGSERIAL PRIMARY KEY, supplier_id BIGINT NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
 rfq_id BIGINT NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE, quote_number VARCHAR(100), quote_date DATE, valid_until DATE,
 currency VARCHAR(10), incoterm VARCHAR(20), delivery_time VARCHAR(100), payment_terms VARCHAR(255), origin VARCHAR(255), warranty VARCHAR(255),
 source_file VARCHAR(1000), source_url VARCHAR(1000), status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED', notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS supplier_quote_lines (
 id BIGSERIAL PRIMARY KEY, supplier_quote_id BIGINT NOT NULL REFERENCES supplier_quotes(id) ON DELETE CASCADE,
 rfq_line_id BIGINT NOT NULL REFERENCES rfq_lines(id) ON DELETE CASCADE, supplier_part_number VARCHAR(255), description TEXT,
 quantity NUMERIC(18,4), unit VARCHAR(50), unit_price NUMERIC(20,6), total_price NUMERIC(20,6), condition VARCHAR(50), brand VARCHAR(255),
 manufacturer VARCHAR(255), lead_time VARCHAR(100), availability VARCHAR(50), technical_compliance VARCHAR(50) NOT NULL DEFAULT 'NOT_REVIEWED', deviation TEXT, notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_suppliers_country ON suppliers(country);
CREATE INDEX IF NOT EXISTS idx_suppliers_type ON suppliers(supplier_type);
CREATE INDEX IF NOT EXISTS idx_supplier_quotes_rfq ON supplier_quotes(rfq_id);
CREATE INDEX IF NOT EXISTS idx_supplier_quote_lines_rfq_line ON supplier_quote_lines(rfq_line_id);

CREATE TABLE IF NOT EXISTS supplier_outreach (
 id BIGSERIAL PRIMARY KEY,
 supplier_id BIGINT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
 rfq_id BIGINT NOT NULL REFERENCES rfqs(id) ON DELETE CASCADE,
 sent_at TIMESTAMPTZ,
 response_at TIMESTAMPTZ,
 status VARCHAR(40) NOT NULL DEFAULT 'SENT',
 channel VARCHAR(40),
 requested_line_count INTEGER,
 responded_line_count INTEGER,
 notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_supplier_outreach_supplier ON supplier_outreach(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_outreach_rfq ON supplier_outreach(rfq_id);
