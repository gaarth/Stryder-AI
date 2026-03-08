-- ═══════ SEED: PORTS ═══════
INSERT INTO ports (id, name, city, latitude, longitude, congestion_level, congestion_pct, capacity, throughput) VALUES
('PRT-MUM', 'Mumbai Port',         'Mumbai',          18.94, 72.84, 'MODERATE', 45, 6000, 250),
('PRT-CHE', 'Chennai Port',        'Chennai',         13.08, 80.29, 'LOW',      30, 5500, 220),
('PRT-VIZ', 'Vishakhapatnam Port', 'Vishakhapatnam',  17.69, 83.22, 'LOW',      25, 4000, 180),
('PRT-KOL', 'Kolkata Port',        'Kolkata',         22.55, 88.35, 'LOW',      28, 4500, 200),
('PRT-KOC', 'Kochi Port',          'Kochi',            9.97, 76.27, 'LOW',      22, 3500, 160),
('PRT-KAN', 'Kandla Port',         'Kandla',          23.03, 70.22, 'LOW',      20, 3000, 150),
('PRT-TUT', 'Tuticorin Port',      'Tuticorin',        8.76, 78.13, 'LOW',      18, 2800, 140),
('PRT-GOA', 'Goa Port',            'Goa',             15.41, 73.88, 'LOW',      15, 2500, 130)
ON CONFLICT (id) DO NOTHING;

-- ═══════ SEED: WAREHOUSES ═══════
INSERT INTO warehouses (id, name, city, latitude, longitude, capacity, utilization_pct) VALUES
('WH-DEL', 'Delhi Warehouse',     'Delhi',      28.61, 77.23, 15000, 55),
('WH-BHO', 'Bhopal Warehouse',    'Bhopal',     23.26, 77.41, 10000, 42),
('WH-NAG', 'Nagpur Warehouse',    'Nagpur',     21.15, 79.09, 12000, 38),
('WH-AHM', 'Ahmedabad Warehouse', 'Ahmedabad',  23.02, 72.57, 11000, 50),
('WH-JAI', 'Jaipur Warehouse',    'Jaipur',     26.91, 75.79,  9000, 35),
('WH-HYD', 'Hyderabad Warehouse', 'Hyderabad',  17.39, 78.49, 13000, 48),
('WH-BEN', 'Bengaluru Warehouse', 'Bengaluru',  12.97, 77.59, 14000, 52),
('WH-LUC', 'Lucknow Warehouse',   'Lucknow',   26.85, 80.95,  8000, 30)
ON CONFLICT (id) DO NOTHING;

-- ═══════ SEED: INITIAL AGENT MEMORY ═══════
INSERT INTO agent_memory (memory_type, content, agent_name) VALUES
('strategy', '{"global_strategy": "balanced"}', 'System'),
('preferences', '{"shipment_priorities": {}}', 'System'),
('learnings', '{"sentinel_detections": 0, "strategist_optimizations": 0, "total_cost_saved": 0, "total_hours_saved": 0}', 'System');
