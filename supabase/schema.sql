-- ═══════════════════════════════════════════
-- STRYDER AI — Full Database Schema
-- ═══════════════════════════════════════════
-- See migration: create_stryder_schema
-- Applied to project: xdgbcjkzjmcksgmuremr

CREATE TABLE ports (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  congestion_level TEXT DEFAULT 'LOW',
  congestion_pct INTEGER DEFAULT 20,
  capacity INTEGER DEFAULT 5000,
  throughput INTEGER DEFAULT 200,
  incoming_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE warehouses (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  city TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  capacity INTEGER DEFAULT 10000,
  utilization_pct INTEGER DEFAULT 40,
  incoming_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE shipments (
  id INTEGER PRIMARY KEY,
  origin_city TEXT NOT NULL,
  origin_id TEXT REFERENCES ports(id) ON DELETE SET NULL,
  destination_city TEXT NOT NULL,
  destination_id TEXT,
  carrier TEXT NOT NULL,
  cargo TEXT,
  status TEXT DEFAULT 'IN_TRANSIT',
  eta_hours INTEGER DEFAULT 0,
  base_cost NUMERIC DEFAULT 0,
  current_cost NUMERIC DEFAULT 0,
  delay_penalty_per_hour NUMERIC DEFAULT 0,
  risk TEXT DEFAULT 'Low',
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  progress INTEGER DEFAULT 0,
  disrupted BOOLEAN DEFAULT FALSE,
  disruption_id INTEGER,
  priority TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE simulation_events (
  id SERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  event_name TEXT,
  severity TEXT DEFAULT 'MEDIUM',
  location TEXT NOT NULL,
  location_id TEXT,
  eta_impact_h INTEGER DEFAULT 0,
  affected_shipments INTEGER[] DEFAULT '{}',
  affected_count INTEGER DEFAULT 0,
  resolved BOOLEAN DEFAULT FALSE,
  scenario_type TEXT,
  timestamp TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE scenario_history (
  id SERIAL PRIMARY KEY,
  scenario_type TEXT NOT NULL,
  disruption_id INTEGER REFERENCES simulation_events(id),
  location TEXT NOT NULL,
  affected_count INTEGER DEFAULT 0,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE agent_memory (
  id SERIAL PRIMARY KEY,
  memory_type TEXT NOT NULL,
  content JSONB DEFAULT '{}',
  agent_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE agent_learning_logs (
  id SERIAL PRIMARY KEY,
  log_message TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  sim_time TEXT,
  confidence NUMERIC DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cascade_alerts (
  id SERIAL PRIMARY KEY,
  alert_type TEXT NOT NULL,
  location TEXT NOT NULL,
  location_id TEXT,
  confidence INTEGER DEFAULT 0,
  potential_impact INTEGER DEFAULT 0,
  impact_count INTEGER DEFAULT 0,
  suggested_action TEXT,
  resolved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE system_metrics (
  id SERIAL PRIMARY KEY,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC DEFAULT 0,
  metric_text TEXT,
  metric_type TEXT DEFAULT 'info',
  sim_time TEXT,
  timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE routes (
  id SERIAL PRIMARY KEY,
  origin_id TEXT NOT NULL,
  destination_id TEXT NOT NULL,
  distance_km NUMERIC DEFAULT 0,
  waypoints JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_carrier ON shipments(carrier);
CREATE INDEX idx_simulation_events_resolved ON simulation_events(resolved);
CREATE INDEX idx_agent_learning_logs_agent ON agent_learning_logs(agent_name);
CREATE INDEX idx_cascade_alerts_resolved ON cascade_alerts(resolved);
CREATE INDEX idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX idx_system_metrics_ts ON system_metrics(timestamp);

-- Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE shipments;
ALTER PUBLICATION supabase_realtime ADD TABLE simulation_events;
ALTER PUBLICATION supabase_realtime ADD TABLE scenario_history;
ALTER PUBLICATION supabase_realtime ADD TABLE cascade_alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE agent_learning_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE system_metrics;
