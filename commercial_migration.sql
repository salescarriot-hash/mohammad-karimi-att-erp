CREATE TABLE IF NOT EXISTS market_prices (
 id BIGSERIAL PRIMARY KEY, part_id BIGINT REFERENCES parts(id) ON DELETE SET NULL, supplier_id BIGINT REFERENCES suppliers(id) ON DELETE SET NULL,
 source_type VARCHAR(50) NOT NULL, source_name VARCHAR(255), source_url VARCHAR(1000), condition VARCHAR(50), brand VARCHAR(255), part_number VARCHAR(255),
 quantity NUMERIC(18,4), unit VARCHAR(50), unit_price NUMERIC(20,6) NOT NULL, currency VARCHAR(10), incoterm VARCHAR(20), lead_time VARCHAR(100), availability VARCHAR(50),
 observed_date DATE, confidence VARCHAR(30) NOT NULL DEFAULT 'MEDIUM', verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING', notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_market_prices_part ON market_prices(part_id);
CREATE INDEX IF NOT EXISTS idx_market_prices_pn ON market_prices(part_number);
CREATE INDEX IF NOT EXISTS idx_market_prices_observed ON market_prices(observed_date);
