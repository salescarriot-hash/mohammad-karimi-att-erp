CREATE TABLE IF NOT EXISTS pricing_settings (
 id BIGSERIAL PRIMARY KEY, default_margin_type VARCHAR(30) NOT NULL DEFAULT 'MARKUP',
 default_margin_value NUMERIC(12,6) NOT NULL DEFAULT 0.05, minimum_margin_type VARCHAR(30),
 minimum_margin_value NUMERIC(12,6), default_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
 rounding_method VARCHAR(30) NOT NULL DEFAULT 'NONE', rounding_value NUMERIC(20,6),
 default_incoterm VARCHAR(20), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pricing_calculations (
 id BIGSERIAL PRIMARY KEY, rfq_line_id BIGINT NOT NULL REFERENCES rfq_lines(id) ON DELETE CASCADE,
 commercial_decision_id BIGINT REFERENCES commercial_decisions(id) ON DELETE SET NULL,
 basis_type VARCHAR(30) NOT NULL DEFAULT 'TARGET_PURCHASE_PRICE', purchase_price NUMERIC(20,6) NOT NULL,
 purchase_currency VARCHAR(10) NOT NULL, exchange_rate NUMERIC(20,8) NOT NULL DEFAULT 1,
 exchange_rate_date DATE, target_currency VARCHAR(10) NOT NULL, freight_cost NUMERIC(20,6) NOT NULL DEFAULT 0,
 insurance_cost NUMERIC(20,6) NOT NULL DEFAULT 0, customs_cost NUMERIC(20,6) NOT NULL DEFAULT 0,
 clearance_cost NUMERIC(20,6) NOT NULL DEFAULT 0, local_delivery_cost NUMERIC(20,6) NOT NULL DEFAULT 0,
 financial_cost NUMERIC(20,6) NOT NULL DEFAULT 0, other_cost NUMERIC(20,6) NOT NULL DEFAULT 0,
 landed_cost NUMERIC(20,6) NOT NULL, margin_type VARCHAR(30) NOT NULL, margin_value NUMERIC(12,6) NOT NULL,
 calculated_selling_price NUMERIC(20,6) NOT NULL, rounding_method VARCHAR(30) NOT NULL DEFAULT 'NONE',
 rounding_value NUMERIC(20,6), final_selling_price NUMERIC(20,6) NOT NULL, incoterm VARCHAR(20), notes TEXT,
 created_by BIGINT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pricing_calculations_rfq_line ON pricing_calculations(rfq_line_id, id DESC);
INSERT INTO pricing_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
