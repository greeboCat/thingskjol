CREATE TABLE laws (
            id INTEGER PRIMARY KEY, filename TEXT UNIQUE, law_nr TEXT, year INTEGER,
            nr_date TEXT, heiti TEXT, title_tag TEXT, effective TEXT, pdf_url TEXT, body_text TEXT
        );
CREATE TABLE chapters (chapter_no TEXT PRIMARY KEY, title TEXT);
CREATE TABLE law_chapters (filename TEXT, chapter_no TEXT, sub_code TEXT, sub_name TEXT);
CREATE TABLE law_amendments (
            filename TEXT, amend_ref TEXT, amend_law_nr TEXT, amend_year INTEGER,
            amend_note TEXT, amend_url TEXT
        );
CREATE VIRTUAL TABLE laws_fts USING fts5(filename UNINDEXED, heiti, body_text)
/* laws_fts(filename,heiti,body_text) */;
CREATE TABLE IF NOT EXISTS 'laws_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE IF NOT EXISTS 'laws_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS 'laws_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2);
CREATE TABLE IF NOT EXISTS 'laws_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE IF NOT EXISTS 'laws_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TABLE regulations (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE, title TEXT, published_date TEXT,
            ministry TEXT, url TEXT, body_text TEXT
        );
CREATE VIRTUAL TABLE regulations_fts USING fts5(name UNINDEXED, title, body_text)
/* regulations_fts(name,title,body_text) */;
CREATE TABLE IF NOT EXISTS 'regulations_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE IF NOT EXISTS 'regulations_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS 'regulations_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2);
CREATE TABLE IF NOT EXISTS 'regulations_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE IF NOT EXISTS 'regulations_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TABLE court_cases (
            id TEXT PRIMARY KEY, title TEXT, court TEXT, case_number TEXT, verdict_date TEXT,
            keywords TEXT, presentings TEXT, url TEXT, full_text TEXT
        );
CREATE VIRTUAL TABLE court_cases_fts USING fts5(
            id UNINDEXED, title, keywords, presentings, full_text
        )
/* court_cases_fts(id,title,keywords,presentings,full_text) */;
CREATE TABLE IF NOT EXISTS 'court_cases_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE IF NOT EXISTS 'court_cases_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS 'court_cases_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4);
CREATE TABLE IF NOT EXISTS 'court_cases_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE IF NOT EXISTS 'court_cases_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TABLE thingmenn (
            id TEXT PRIMARY KEY, nafn TEXT, faedingardagur TEXT, lifshlaup_text TEXT
        );
CREATE VIRTUAL TABLE thingmenn_fts USING fts5(id UNINDEXED, nafn, lifshlaup_text)
/* thingmenn_fts(id,nafn,lifshlaup_text) */;
CREATE TABLE IF NOT EXISTS 'thingmenn_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE IF NOT EXISTS 'thingmenn_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS 'thingmenn_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2);
CREATE TABLE IF NOT EXISTS 'thingmenn_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE IF NOT EXISTS 'thingmenn_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TABLE thingmenn_thingseta (
            thingmadur_id TEXT, thing TEXT, tegund TEXT, thingflokkur TEXT,
            kjordaemi TEXT, inn TEXT, ut TEXT
        );
CREATE TABLE thingmenn_nefndaseta (
            thingmadur_id TEXT, nefnd TEXT, hlutverk TEXT, thing TEXT
        );
CREATE TABLE alyktanir (
            id TEXT PRIMARY KEY, thing INTEGER, malnr TEXT, heiti TEXT, stada TEXT,
            efnisflokkar TEXT, skjalnr TEXT, url TEXT, full_text TEXT
        );
CREATE VIRTUAL TABLE alyktanir_fts USING fts5(
            id UNINDEXED, heiti, efnisflokkar, full_text
        )
/* alyktanir_fts(id,heiti,efnisflokkar,full_text) */;
CREATE TABLE IF NOT EXISTS 'alyktanir_fts_data'(id INTEGER PRIMARY KEY, block BLOB);
CREATE TABLE IF NOT EXISTS 'alyktanir_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS 'alyktanir_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3);
CREATE TABLE IF NOT EXISTS 'alyktanir_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);
CREATE TABLE IF NOT EXISTS 'alyktanir_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;
CREATE TABLE embedding_chunks (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    title TEXT,
    UNIQUE(source_type, source_id, chunk_index)
);
CREATE INDEX idx_embedding_chunks_source ON embedding_chunks(source_type, source_id);
