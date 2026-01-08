-- PostgreSQL schema for protobuf benchmark
-- Separate tables for binary and JSON to avoid WHERE queries

DROP TABLE IF EXISTS infra_exec_binary;
DROP TABLE IF EXISTS infra_exec_json;

-- Binary protobuf table (BYTEA column)
CREATE TABLE infra_exec_binary (
    id BIGSERIAL PRIMARY KEY,
    payload BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- JSON protobuf table (JSONB column)
CREATE TABLE infra_exec_json (
    id BIGSERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
