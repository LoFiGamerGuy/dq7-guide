PRAGMA foreign_keys = ON;

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    publisher TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_class TEXT NOT NULL,
    role TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT,
    retrieved_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT
);

CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    canonical_key TEXT NOT NULL UNIQUE,
    description TEXT,
    reconstruction_status TEXT NOT NULL DEFAULT 'native'
);

CREATE TABLE relationships (
    relationship_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES entities(entity_id),
    predicate TEXT NOT NULL,
    object_id TEXT NOT NULL REFERENCES entities(entity_id),
    qualifier_json TEXT NOT NULL DEFAULT '{}',
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    confidence TEXT NOT NULL,
    UNIQUE(subject_id, predicate, object_id, qualifier_json, source_id)
);

CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    subject_key TEXT NOT NULL,
    predicate TEXT NOT NULL,
    value_json TEXT NOT NULL,
    claim_kind TEXT NOT NULL,
    scope_json TEXT NOT NULL DEFAULT '{}',
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT,
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    reconstruction_status TEXT NOT NULL DEFAULT 'native',
    notes TEXT
);

CREATE INDEX claims_lookup ON claims(subject_key, predicate);

CREATE TABLE conflicts (
    conflict_id TEXT PRIMARY KEY,
    conflict_key TEXT NOT NULL,
    claim_a_id TEXT NOT NULL REFERENCES claims(claim_id),
    claim_b_id TEXT NOT NULL REFERENCES claims(claim_id),
    status TEXT NOT NULL,
    resolution_claim_id TEXT REFERENCES claims(claim_id),
    rationale TEXT,
    UNIQUE(claim_a_id, claim_b_id)
);

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    domain TEXT NOT NULL,
    checkpoint_key TEXT,
    source_id TEXT REFERENCES sources(source_id),
    locator TEXT,
    confidence TEXT NOT NULL,
    reconstruction_status TEXT NOT NULL DEFAULT 'native'
);

CREATE VIRTUAL TABLE document_fts USING fts5(
    title,
    body,
    domain,
    checkpoint_key,
    content='documents',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO document_fts(rowid, title, body, domain, checkpoint_key)
    VALUES (new.rowid, new.title, new.body, new.domain, new.checkpoint_key);
END;

CREATE TRIGGER documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO document_fts(document_fts, rowid, title, body, domain, checkpoint_key)
    VALUES ('delete', old.rowid, old.title, old.body, old.domain, old.checkpoint_key);
END;

CREATE TRIGGER documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO document_fts(document_fts, rowid, title, body, domain, checkpoint_key)
    VALUES ('delete', old.rowid, old.title, old.body, old.domain, old.checkpoint_key);
    INSERT INTO document_fts(rowid, title, body, domain, checkpoint_key)
    VALUES (new.rowid, new.title, new.body, new.domain, new.checkpoint_key);
END;

CREATE TABLE vocations (
    vocation_id TEXT PRIMARY KEY REFERENCES entities(entity_id),
    tier TEXT NOT NULL,
    exclusive_character TEXT,
    let_loose TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE vocation_requirements (
    requirement_id TEXT PRIMARY KEY,
    vocation_id TEXT NOT NULL REFERENCES vocations(vocation_id),
    group_id TEXT NOT NULL,
    rule TEXT NOT NULL,
    required_count INTEGER NOT NULL,
    prerequisite_vocation_id TEXT NOT NULL REFERENCES vocations(vocation_id),
    source_id TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE medal_rewards (
    threshold INTEGER PRIMARY KEY,
    reward TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    confidence TEXT NOT NULL
);

CREATE TABLE missables (
    missable_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    available_from TEXT,
    unavailable_after TEXT,
    consequence TEXT NOT NULL,
    severity TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL
);

CREATE TABLE farming_spots (
    farming_id TEXT PRIMARY KEY,
    target TEXT NOT NULL,
    location TEXT NOT NULL,
    time_period TEXT,
    available_from TEXT,
    strategy TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    confidence TEXT NOT NULL
);

CREATE TABLE checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    sequence_no INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    time_period TEXT,
    region TEXT,
    entry_condition TEXT,
    safe_exit_condition TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    confidence TEXT NOT NULL,
    coverage_status TEXT NOT NULL
);

