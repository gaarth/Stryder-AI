import { useState, useEffect, useRef, useCallback } from 'react';
import OpsMap from '../components/OpsMap';
import AgentTerminal from '../components/AgentTerminal';
import CRMTable from '../components/CRMTable';
import MetricsFeed from '../components/MetricsFeed';
import ShipmentDetail from '../components/ShipmentDetail';
import Dashboard from '../components/Dashboard';
import './Terminal.css';

const _BACKEND = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const API = `${_BACKEND}/api/ops`;
const CHAT_API = `${_BACKEND}/api/chat`;

async function post(path, data) {
    const r = await fetch(`${API}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data || {}) });
    return r.json();
}
async function get(path) { const r = await fetch(`${API}${path}`); return r.json(); }

export default function Terminal() {
    const [state, setState] = useState(null);
    const [loading, setLoading] = useState('');
    const [selectedShipment, setSelectedShipment] = useState(null);
    const [view, setView] = useState('terminal');
    const [portDetail, setPortDetail] = useState(null);
    const [whDetail, setWhDetail] = useState(null);
    const [scenarioOpen, setScenarioOpen] = useState(false);

    // Sim controls (local state synced from server)
    const [simPaused, setSimPaused] = useState(false);
    const [simSpeed, setSimSpeed] = useState(1.0);
    const [moveScale, setMoveScale] = useState(1.0);
    const [simFrozen, setSimFrozen] = useState(false);
    const [autoMode, setAutoMode] = useState(true);

    const [termMessages, setTermMessages] = useState([
        { role: 'system', text: 'STRYDER AI Operations Terminal v3\nIntent-driven agent orchestration active.\n\nAgents: @Sentinel @Strategist @Actuary @Executor @Cascade\nSubtags: :ETA_AGENT :CARRIER_AGENT :DELAY_AGENT :HUB_AGENT :COST_AGENT\n\nType /help for commands.' },
    ]);
    const agentQueueRef = useRef([]);
    const displayingRef = useRef(false);

    // Poll state
    const refresh = useCallback(async () => {
        try {
            const s = await get('/state');
            setState(s);
            setAutoMode(s.auto_mode);
            setSimPaused(s.sim_paused);
            setSimSpeed(s.sim_speed);
            setMoveScale(s.movement_scale);
            setSimFrozen(s.sim_frozen);
        } catch (e) { console.error(e); }
    }, []);
    useEffect(() => { refresh(); const id = setInterval(refresh, 2500); return () => clearInterval(id); }, [refresh]);

    // Progressive terminal display
    const enqueueAgentSteps = useCallback((steps, disruptionMsg) => {
        if (disruptionMsg) {
            agentQueueRef.current.push({ role: 'disruption', text: disruptionMsg, immediate: true });
        }
        steps.forEach(step => {
            agentQueueRef.current.push({
                role: 'agent', agent: step.agent,
                text: step.bullets.map(b => `• ${b}`).join('\n'),
                rerouted_ids: step.rerouted_ids || null,
                fix_details: step.fix_details || null,
            });
        });
        processQueue();
    }, []);

    const processQueue = useCallback(() => {
        if (displayingRef.current || agentQueueRef.current.length === 0) return;
        displayingRef.current = true;
        const next = agentQueueRef.current.shift();
        if (next.immediate) {
            setTermMessages(prev => [...prev, { ...next, typing: false }]);
            displayingRef.current = false;
            processQueue();
        } else {
            setTermMessages(prev => [...prev, { ...next, typing: true }]);
            const dur = Math.min(2000, 300 + next.text.length * 8);
            setTimeout(() => {
                setTermMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, typing: false } : m));
                setTimeout(() => { displayingRef.current = false; processQueue(); }, 400);
            }, dur);
        }
    }, []);

    // ── SIM CONTROL ACTIONS ──
    const sendSimControl = async (patch) => {
        await post('/sim-control', patch);
        await refresh();
    };
    const handlePause = () => sendSimControl({ paused: !simPaused });
    const handleFreeze = () => sendSimControl({ frozen: !simFrozen });
    const handleSpeedChange = (v) => sendSimControl({ speed: v });
    const handleMoveScaleChange = (v) => sendSimControl({ movement_scale: v });
    const handleStepTick = async () => { setLoading('tick'); await post('/tick'); await refresh(); setLoading(''); };

    // ── DISRUPTION / AGENT / SCENARIO ──
    const handleDisrupt = async () => {
        setLoading('disrupt');
        try {
            const result = await post('/disrupt');
            const d = result.disruption;
            const msg = `⚡ ${d.name} at ${d.location}\n${d.affected_count} shipments affected — ETA +${d.eta_impact_h}h\nSeverity: ${d.severity}`;
            if (result.auto_resolved && result.agent_steps?.length) {
                enqueueAgentSteps(result.agent_steps, msg);
            } else {
                setTermMessages(prev => [...prev, { role: 'disruption', text: msg }]);
            }
        } catch (e) { console.error(e); }
        await refresh(); setLoading('');
    };
    const handleScenario = async (type) => {
        setScenarioOpen(false);
        setLoading('scenario');
        try {
            const result = await post('/scenario', { scenario_type: type });
            if (result.error) {
                setTermMessages(prev => [...prev, { role: 'system', text: `Scenario error: ${result.error}` }]);
            } else {
                const d = result.disruption;
                const msg = `🎯 Scenario: ${d.name} at ${d.location}\n${d.affected_count} shipments affected — ETA +${d.eta_impact_h}h\nSeverity: ${d.severity}`;
                if (result.auto_resolved && result.agent_steps?.length) {
                    enqueueAgentSteps(result.agent_steps, msg);
                } else {
                    setTermMessages(prev => [...prev, { role: 'disruption', text: msg }]);
                }
            }
        } catch (e) { console.error(e); }
        await refresh(); setLoading('');
    };
    const handleRunAgents = async () => {
        setLoading('agents');
        try {
            const r = await post('/run-agents');
            if (r.agent_steps?.length) enqueueAgentSteps(r.agent_steps);
            else setTermMessages(prev => [...prev, { role: 'system', text: 'No unresolved disruptions. Agents idle.' }]);
        } catch (e) { console.error(e); }
        await refresh(); setLoading('');
    };
    const handleReset = async () => {
        await post('/reset');
        setTermMessages([{ role: 'system', text: 'Simulation reset — 120 fresh shipments.' }]);
        agentQueueRef.current = []; displayingRef.current = false;
        await refresh();
    };
    const handleToggleMode = async () => {
        await fetch(`${API}/mode?auto=${!autoMode}`, { method: 'POST' });
        setAutoMode(!autoMode);
    };

    const handleChat = async (msg) => {
        setTermMessages(prev => [...prev, { role: 'user', text: msg }]);
        // Slash commands
        if (msg === '/help') {
            setTermMessages(prev => [...prev, { role: 'system', text: 'Commands:\n/help — this message\n/reset — reset simulation\n/status — system overview\n/shipment <id> — view detail\n/strategy <cost|speed|balanced>\n\nAgent commands:\n@Sentinel scan\n@Strategist:ETA_AGENT optimize shipment 13\n@Strategist:CARRIER_AGENT shipment 13\n@Actuary estimate cost impact\n@Cascade analyze risk\nApply option 1/2/3\n\nWhat have you learned so far?' }]);
            return;
        }
        if (msg === '/reset') { await handleReset(); return; }
        if (msg === '/status') {
            const s = state?.stats || {};
            setTermMessages(prev => [...prev, { role: 'system', text: `Total: ${s.total} | Transit: ${s.in_transit} | Delayed: ${s.delayed} | Delivered: ${s.delivered}\nStrategy: ${(state?.global_strategy || 'balanced').toUpperCase()}` }]);
            return;
        }
        if (msg.startsWith('/shipment ')) {
            const id = parseInt(msg.split(' ')[1]);
            const ship = state?.shipments?.find(s => s.id === id);
            if (ship) { setSelectedShipment(ship); return; }
            setTermMessages(prev => [...prev, { role: 'system', text: `Shipment #${id} not found.` }]);
            return;
        }
        if (msg.startsWith('/strategy ')) {
            const strat = msg.split(' ')[1]?.toLowerCase();
            if (['cost', 'speed', 'balanced'].includes(strat)) {
                await post('/strategy', { strategy: strat });
                setTermMessages(prev => [...prev, { role: 'system', text: `✓ Strategy set to: ${strat.toUpperCase()}` }]);
                await refresh();
                return;
            }
        }

        // Agent chat (via intent pipeline)
        try {
            setTermMessages(prev => [...prev, { role: 'thinking', agent: 'Classifying', text: '' }]);
            const r = await fetch(`${CHAT_API}/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
            const data = await r.json();
            setTermMessages(prev => {
                const f = prev.filter(m => m.role !== 'thinking');
                return [...f, { role: 'agent', agent: data.agent, text: data.response, typing: true }];
            });
            setTimeout(() => {
                setTermMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, typing: false } : m));
            }, Math.min(3000, 400 + data.response.length * 5));
            await refresh();
        } catch (e) {
            setTermMessages(prev => prev.filter(m => m.role !== 'thinking'));
            setTermMessages(prev => [...prev, { role: 'system', text: `Error: ${e.message}` }]);
        }
    };

    const handleShipmentClick = (id) => {
        const ship = state?.shipments?.find(s => s.id === id); if (ship) setSelectedShipment(ship);
    };
    const handleCascadeFix = async (alert) => { setView('terminal'); handleChat(`@Strategist reroute shipments near ${alert.location} — ${alert.suggestion}`); };
    const handleOptimize = async (shipId) => { setSelectedShipment(null); handleChat(`@Strategist:ETA_AGENT optimize shipment ${shipId}`); };

    const stats = state?.stats || {};
    const simTime = state?.sim_time ? new Date(state.sim_time).toLocaleTimeString('en-GB', { hour12: false }) : '--:--';
    const strategy = state?.global_strategy || 'balanced';

    const SCENARIOS = [
        { type: 'PORT_CONGESTION', label: 'Port Congestion', severity: 'HIGH' },
        { type: 'CARRIER_STRIKE', label: 'Carrier Strike', severity: 'HIGH' },
        { type: 'WEATHER_DISRUPTION', label: 'Weather Disruption', severity: 'MEDIUM' },
        { type: 'WAREHOUSE_OVERFLOW', label: 'Warehouse Overflow', severity: 'MEDIUM' },
        { type: 'CUSTOMS_DELAY', label: 'Customs Delay', severity: 'LOW' },
        { type: 'ROUTE_BLOCKAGE', label: 'Route Blockage', severity: 'HIGH' },
    ];

    return (
        <div className="term-layout">
            {/* TOP BAR */}
            <div className="top-bar">
                <div className="top-left">
                    <span className="logo">STRYDER</span>
                    <span className="logo-tag">OPS</span>
                    <div className="nav-tabs">
                        <button className={`nav-tab ${view === 'terminal' ? 'active' : ''}`} onClick={() => setView('terminal')}>Terminal</button>
                        <button className={`nav-tab ${view === 'dashboard' ? 'active' : ''}`} onClick={() => setView('dashboard')}>Dashboard</button>
                    </div>
                    <span className="sep">│</span>
                    <span className="stat">T{state?.time_tick || 0}</span>
                    <span className="stat">{simTime}</span>
                    <span className="sep">│</span>
                    <span className="stat st-transit">{stats.in_transit || 0}▲</span>
                    <span className="stat st-delayed">{stats.delayed || 0}▼</span>
                    <span className="stat st-delivered">{stats.delivered || 0}✓</span>
                    <span className="sep">│</span>
                    <span className={`stat strategy-${strategy}`}>⚙{strategy.toUpperCase()}</span>
                </div>
                <div className="top-right">
                    {/* SIM CONTROLS */}
                    <div className="sim-controls">
                        <button className={`sc-btn ${simPaused ? 'paused' : ''}`} onClick={handlePause} title={simPaused ? 'Resume Sim' : 'Pause Sim'}>
                            {simPaused ? '▶' : '⏸'}
                        </button>
                        <button className="sc-btn" onClick={handleStepTick} title="Step +1 Tick">+1</button>
                        <div className="sc-slider-group" title={`Speed: ${simSpeed}x`}>
                            <span className="sc-label">SPD</span>
                            <select className="sc-select" value={simSpeed} onChange={e => handleSpeedChange(parseFloat(e.target.value))}>
                                <option value="0.25">0.25×</option>
                                <option value="0.5">0.5×</option>
                                <option value="1">1×</option>
                                <option value="2">2×</option>
                                <option value="5">5×</option>
                            </select>
                        </div>
                        <div className="sc-slider-group" title={`Movement: ${moveScale * 100}%`}>
                            <span className="sc-label">MOV</span>
                            <select className="sc-select" value={moveScale} onChange={e => handleMoveScaleChange(parseFloat(e.target.value))}>
                                <option value="0">0%</option>
                                <option value="0.25">25%</option>
                                <option value="0.5">50%</option>
                                <option value="1">100%</option>
                            </select>
                        </div>
                        <button className={`sc-btn ${simFrozen ? 'frozen' : ''}`} onClick={handleFreeze} title={simFrozen ? 'Unfreeze' : 'Freeze State'}>
                            {simFrozen ? '🔓' : '❄'}
                        </button>
                    </div>
                    <span className="sep">│</span>
                    <button className={`tb ${loading === 'disrupt' ? 'loading' : ''}`} onClick={handleDisrupt}>⚡ Random</button>
                    <div className="scenario-wrap">
                        <button className={`tb tb-scenario ${loading === 'scenario' ? 'loading' : ''}`} onClick={() => setScenarioOpen(!scenarioOpen)}>🎯 Scenario ▾</button>
                        {scenarioOpen && (
                            <div className="scenario-dropdown">
                                {SCENARIOS.map(s => (
                                    <button key={s.type} className="scenario-item" onClick={() => handleScenario(s.type)}>
                                        <span className={`sev-dot sev-${s.severity.toLowerCase()}`}></span>
                                        {s.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                    <button className={`tb ${loading === 'agents' ? 'loading' : ''}`} onClick={handleRunAgents}>▶ Agents</button>
                    <button className={`tb tb-mode ${autoMode ? 'auto' : 'manual'}`} onClick={handleToggleMode}>{autoMode ? 'AUTO' : 'MANUAL'}</button>
                    <button className="tb tb-reset" onClick={handleReset}>↻</button>
                </div>
            </div>

            {view === 'terminal' ? (
                <div className="main-grid">
                    <div className="left-col">
                        <div className="map-container">
                            <OpsMap
                                shipments={state?.shipments || []}
                                ports={state?.ports || []}
                                warehouses={state?.warehouses || []}
                                onSelectShipment={setSelectedShipment}
                                onPortClick={p => setPortDetail(p)}
                                onWhClick={w => setWhDetail(w)}
                            />
                        </div>
                        <div className="crm-container">
                            <CRMTable shipments={state?.shipments || []} onSelectShipment={setSelectedShipment} />
                        </div>
                    </div>
                    <div className="right-col">
                        <div className="terminal-container">
                            <AgentTerminal messages={termMessages} onSend={handleChat} onShipmentClick={handleShipmentClick} />
                        </div>
                        <div className="metrics-container">
                            <MetricsFeed entries={state?.metrics_log || []} />
                        </div>
                    </div>
                </div>
            ) : (
                <div className="dashboard-view">
                    <Dashboard
                        agentStats={state?.agent_stats || {}}
                        agentMemory={state?.agent_memory_summary || {}}
                        eventLog={state?.event_log || []}
                        cascadeAlerts={state?.cascade_alerts || []}
                        learningLogs={state?.learning_logs || []}
                        scenarioHistory={state?.scenario_history || []}
                        onCascadeFix={handleCascadeFix}
                    />
                </div>
            )}

            {/* Shipment detail modal */}
            {selectedShipment && (
                <ShipmentDetail
                    shipment={selectedShipment}
                    onClose={() => setSelectedShipment(null)}
                    onOptimize={handleOptimize}
                    onAskAgent={(id) => { setSelectedShipment(null); handleChat(`@Strategist analyze shipment #${id}`); }}
                    onDismissUpdate={async (id) => { await fetch(`${API}/shipment/${id}/dismiss`, { method: 'POST' }); await refresh(); }}
                />
            )}

            {/* Port detail modal */}
            {portDetail && (
                <div className="modal-overlay" onClick={() => setPortDetail(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 360 }}>
                        <div className="modal-header">
                            <span>⚓ {portDetail.name}</span>
                            <button className="modal-close" onClick={() => setPortDetail(null)}>✕</button>
                        </div>
                        <div className="modal-body" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                            <div className="info-grid">
                                <span className="info-label">Congestion</span>
                                <span className={`info-val cong-${portDetail.congestion_level?.toLowerCase()}`}>{portDetail.congestion_level} ({portDetail.congestion_pct}%)</span>
                                <span className="info-label">Throughput</span>
                                <span className="info-val">{portDetail.throughput} TEU/day</span>
                                <span className="info-label">Incoming</span>
                                <span className="info-val">{portDetail.incoming_count} shipments</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Warehouse detail modal */}
            {whDetail && (
                <div className="modal-overlay" onClick={() => setWhDetail(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 360 }}>
                        <div className="modal-header">
                            <span>▪ {whDetail.name}</span>
                            <button className="modal-close" onClick={() => setWhDetail(null)}>✕</button>
                        </div>
                        <div className="modal-body" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                            <div className="info-grid">
                                <span className="info-label">Capacity</span>
                                <span className="info-val">{whDetail.capacity} units</span>
                                <span className="info-label">Utilization</span>
                                <span className={`info-val ${whDetail.utilization_pct > 80 ? 'text-red' : ''}`}>{whDetail.utilization_pct}%</span>
                                <span className="info-label">Incoming</span>
                                <span className="info-val">{whDetail.incoming_count} shipments</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
