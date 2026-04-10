CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE rule_nodes (
    id UUID PRIMARY KEY,
    parent_id UUID,
    node_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(255),
    operator VARCHAR(50),
    node_value JSONB,
    citation TEXT,
    description VARCHAR(255),
    page_number VARCHAR(50),
    line_number VARCHAR(50),
    run_name VARCHAR(255)
);

CREATE TABLE test_encounters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    encounter_json JSONB NOT NULL,
    target_rule_id UUID NOT NULL,
    expected_to_pass BOOLEAN NOT NULL,
    run_name VARCHAR(255)
);
