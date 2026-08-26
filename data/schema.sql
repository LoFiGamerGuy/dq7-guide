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
    detection_method TEXT NOT NULL DEFAULT 'manual',
    CHECK(claim_a_id < claim_b_id),
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

CREATE TABLE mini_medal_locations (
    medal_number INTEGER PRIMARY KEY CHECK(medal_number BETWEEN 1 AND 100),
    location TEXT NOT NULL,
    detail TEXT NOT NULL,
    time_period TEXT,
    checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id),
    available_checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id),
    available_from TEXT,
    unavailable_after TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL
);

CREATE TABLE mini_medal_evidence (
    evidence_id TEXT PRIMARY KEY,
    medal_number INTEGER NOT NULL REFERENCES mini_medal_locations(medal_number),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    source_ordinal INTEGER,
    ordinal_scheme TEXT,
    notes TEXT,
    UNIQUE(medal_number, source_id, locator)
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


CREATE TABLE checkpoint_obligations (
    obligation_id TEXT PRIMARY KEY,
    checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id),
    obligation_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    action TEXT NOT NULL,
    required_for_100_percent INTEGER NOT NULL CHECK(required_for_100_percent IN (0, 1)),
    stop_before_advancing INTEGER NOT NULL CHECK(stop_before_advancing IN (0, 1)),
    available_from TEXT,
    unavailable_after TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL
);

CREATE TABLE checkpoint_advice (
    advice_id TEXT PRIMARY KEY,
    checkpoint_id TEXT NOT NULL REFERENCES checkpoints(checkpoint_id),
    advice_type TEXT NOT NULL CHECK(advice_type IN ('gear', 'boss', 'grind', 'vocation')),
    subject TEXT NOT NULL CHECK(length(trim(subject)) > 0),
    advice_text TEXT NOT NULL CHECK(length(trim(advice_text)) > 0),
    recommendation_goal TEXT NOT NULL CHECK(
        recommendation_goal IN ('completion_safe', 'immediate_power', 'both')
    ),
    display_order INTEGER NOT NULL CHECK(display_order >= 0),
    applicability_json TEXT NOT NULL DEFAULT '{}',
    ready_for_play INTEGER NOT NULL CHECK(ready_for_play IN (0, 1)),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    UNIQUE(checkpoint_id, advice_type, display_order)
);


CREATE TABLE item_categories (
    category_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    heroic_hoarder_order INTEGER NOT NULL UNIQUE
);

CREATE TABLE items (
    item_id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES item_categories(category_id),
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    canonical_key TEXT NOT NULL UNIQUE,
    heroic_hoarder_ordinal INTEGER,
    heroic_hoarder_required INTEGER NOT NULL CHECK(heroic_hoarder_required IN (0, 1)),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    UNIQUE(category_id, heroic_hoarder_ordinal)
);

CREATE TABLE item_acquisition_paths (
    acquisition_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES items(item_id),
    method TEXT NOT NULL CHECK(method IN (
        'shop', 'chest', 'drop', 'reward', 'lucky_panel', 'arena',
        'medal_exchange', 'story', 'dlc', 'steal', 'other'
    )),
    route_label TEXT NOT NULL,
    location_text TEXT,
    time_period TEXT CHECK(time_period IN ('Past', 'Present', 'Both', 'Unknown') OR time_period IS NULL),
    available_from_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    unavailable_after_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    prerequisite_json TEXT NOT NULL DEFAULT '{}',
    quantity INTEGER CHECK(quantity IS NULL OR quantity > 0),
    supply_type TEXT NOT NULL CHECK(supply_type IN ('finite', 'renewable', 'unknown')),
    finite_total INTEGER CHECK(
        finite_total IS NULL OR (supply_type = 'finite' AND finite_total > 0)
    ),
    is_free INTEGER CHECK(is_free IN (0, 1) OR is_free IS NULL),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL
);

CREATE INDEX acquisition_by_item
    ON item_acquisition_paths(item_id, available_from_checkpoint_id, method);

CREATE TABLE shops (
    shop_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    time_period TEXT NOT NULL CHECK(time_period IN ('Past', 'Present', 'Both', 'Unknown')),
    available_from_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    unavailable_after_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL
);

CREATE TABLE shop_inventory (
    acquisition_id TEXT PRIMARY KEY REFERENCES item_acquisition_paths(acquisition_id),
    shop_id TEXT NOT NULL REFERENCES shops(shop_id),
    price INTEGER NOT NULL CHECK(price >= 0),
    currency TEXT NOT NULL DEFAULT 'gold',
    stock_limit INTEGER CHECK(stock_limit IS NULL OR stock_limit > 0)
);

CREATE TABLE lucky_panel_pools (
    pool_id TEXT PRIMARY KEY,
    venue TEXT NOT NULL,
    game_version TEXT NOT NULL,
    panel_rank TEXT NOT NULL,
    chest_tier TEXT NOT NULL,
    time_period TEXT NOT NULL CHECK(time_period IN ('Past', 'Present', 'Both', 'Unknown')),
    available_from_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    unavailable_after_checkpoint_id TEXT REFERENCES checkpoints(checkpoint_id),
    entry_cost INTEGER CHECK(entry_cost IS NULL OR entry_cost >= 0),
    currency TEXT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    locator TEXT NOT NULL CHECK(length(trim(locator)) > 0),
    confidence TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    UNIQUE(venue, game_version, panel_rank, chest_tier, time_period)
);

CREATE TABLE lucky_panel_rewards (
    acquisition_id TEXT PRIMARY KEY REFERENCES item_acquisition_paths(acquisition_id),
    pool_id TEXT NOT NULL REFERENCES lucky_panel_pools(pool_id),
    reward_quantity INTEGER NOT NULL DEFAULT 1 CHECK(reward_quantity > 0),
    slot_count INTEGER CHECK(slot_count IS NULL OR slot_count > 0),
    probability_text TEXT
);
