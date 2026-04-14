-- SPAM Gmail — initial schema
-- Neon Postgres. Idempotent — safe to re-run.

CREATE TABLE IF NOT EXISTS raw_emails (
  id TEXT PRIMARY KEY,
  thread_id TEXT,
  sender TEXT NOT NULL,
  sender_domain TEXT NOT NULL,
  subject TEXT,
  snippet TEXT,
  labels TEXT[],
  received_at TIMESTAMPTZ NOT NULL,
  fetched_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_raw_emails_received_at ON raw_emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_emails_sender_domain ON raw_emails(sender_domain);

CREATE TABLE IF NOT EXISTS decisions (
  email_id TEXT REFERENCES raw_emails(id) ON DELETE CASCADE,
  decision TEXT NOT NULL CHECK (decision IN ('spam', 'keep', 'uncertain')),
  confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  model_version TEXT NOT NULL,
  used_llm BOOLEAN DEFAULT FALSE,
  llm_reasoning TEXT,
  decided_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (email_id, model_version)
);

-- Shadow-mode observations: co user zrobił z mailem (kasuje, czyta, zostawia)
CREATE TABLE IF NOT EXISTS observations (
  email_id TEXT REFERENCES raw_emails(id) ON DELETE CASCADE PRIMARY KEY,
  final_state TEXT NOT NULL CHECK (final_state IN ('deleted', 'read_kept', 'unread_kept', 'archived', 'starred', 'spam_folder')),
  observed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
  email_id TEXT REFERENCES raw_emails(id) ON DELETE CASCADE PRIMARY KEY,
  user_label TEXT NOT NULL CHECK (user_label IN ('spam', 'keep')),
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  email_id TEXT,
  action TEXT NOT NULL,
  performed_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_audit_log_performed_at ON audit_log(performed_at DESC);
