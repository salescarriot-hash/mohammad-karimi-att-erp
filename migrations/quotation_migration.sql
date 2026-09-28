CREATE TABLE IF NOT EXISTS quotations (
 id BIGSERIAL PRIMARY KEY, quotation_number VARCHAR(100) UNIQUE NOT NULL, rfq_id BIGINT NOT NULL REFERENCES rfqs(id) ON DELETE RESTRICT,
 case_id BIGINT NOT NULL REFERENCES cases(id) ON DELETE RESTRICT, customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
 contact_id BIGINT REFERENCES customer_contacts(id) ON DELETE SET NULL, quotation_date DATE NOT NULL, valid_until DATE,
 currency VARCHAR(10), incoterm VARCHAR(20), delivery_location VARCHAR(255), payment_terms TEXT, delivery_time VARCHAR(255), warranty VARCHAR(255), origin VARCHAR(255),
 price_basis VARCHAR(50), subtotal NUMERIC(20,6) NOT NULL DEFAULT 0, discount NUMERIC(20,6) NOT NULL DEFAULT 0, additional_cost NUMERIC(20,6) NOT NULL DEFAULT 0,
 grand_total NUMERIC(20,6) NOT NULL DEFAULT 0, status VARCHAR(40) NOT NULL DEFAULT 'DRAFT', source_template VARCHAR(500), customer_notes TEXT, internal_notes TEXT,
 created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS quotation_lines (
 id BIGSERIAL PRIMARY KEY, quotation_id BIGINT NOT NULL REFERENCES quotations(id) ON DELETE CASCADE, rfq_line_id BIGINT NOT NULL REFERENCES rfq_lines(id) ON DELETE RESTRICT,
 line_number INT NOT NULL, description TEXT, part_id BIGINT REFERENCES parts(id) ON DELETE SET NULL, manufacturer VARCHAR(255), part_number VARCHAR(255), brand VARCHAR(255), quantity NUMERIC(18,4), unit VARCHAR(50), condition VARCHAR(50),
 supplier_quote_line_id BIGINT REFERENCES supplier_quote_lines(id) ON DELETE SET NULL, target_purchase_price NUMERIC(20,6), actual_purchase_price NUMERIC(20,6), purchase_currency VARCHAR(10), exchange_rate NUMERIC(20,8), exchange_rate_date DATE,
 freight_cost NUMERIC(20,6) DEFAULT 0, insurance_cost NUMERIC(20,6) DEFAULT 0, customs_cost NUMERIC(20,6) DEFAULT 0, clearance_cost NUMERIC(20,6) DEFAULT 0, local_delivery_cost NUMERIC(20,6) DEFAULT 0, financial_cost NUMERIC(20,6) DEFAULT 0, other_cost NUMERIC(20,6) DEFAULT 0,
 landed_cost NUMERIC(20,6), margin_type VARCHAR(30), margin_value NUMERIC(12,6), calculated_selling_price NUMERIC(20,6), manual_selling_price NUMERIC(20,6), final_selling_price NUMERIC(20,6), selling_total_price NUMERIC(20,6), currency VARCHAR(10), delivery_time VARCHAR(255), origin VARCHAR(255), warranty VARCHAR(255),
 technical_compliance VARCHAR(40), deviation TEXT, verification_status VARCHAR(40), pricing_status VARCHAR(40), override_reason TEXT, notes TEXT, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_quotations_rfq_id ON quotations(rfq_id);
CREATE INDEX IF NOT EXISTS ix_quotation_lines_quotation_id ON quotation_lines(quotation_id);
CREATE INDEX IF NOT EXISTS ix_quotation_lines_rfq_line_id ON quotation_lines(rfq_line_id);
