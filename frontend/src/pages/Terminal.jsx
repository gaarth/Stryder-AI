import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import OpsMap from '../components/OpsMap';
import AgentTerminal from '../components/AgentTerminal';
import CRMTable from '../components/CRMTable';
import MetricsFeed from '../components/MetricsFeed';
import ShipmentDetail from '../components/ShipmentDetail';
import Dashboard from '../components/Dashboard';
import AgentsLearningHub from '../components/AgentsLearningHub';
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
    const [showControlPanel, setShowControlPanel] = useState(false);

    // CRM Filters (shared with map)
    const [crmFilters, setCrmFilters] = useState({ status: [], carrier: [], origin: [], destination: [] });

    // Sim controls (local state synced from server)
    const [simPaused, setSimPaused] = useState(false);
    const [simSpeed, setSimSpeed] = useState(1.0);
    const [moveScale, setMoveScale] = useState(1.0);
    const [simFrozen, setSimFrozen] = useState(false);
    const [autoMode, setAutoMode] = useState(true);
    const [showThinking, setShowThinking] = useState(null); // holds thought steps for expandable view
    const [mapTheme, setMapTheme] = useState('dark');

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
            const msg = `EVENT: ${d.name} at ${d.location}\n${d.affected_count} shipments affected — ETA +${d.eta_impact_h}h\nSeverity: ${d.severity}`;
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
                const msg = `Scenario: ${d.name} at ${d.location}\n${d.affected_count} shipments affected — ETA +${d.eta_impact_h}h\nSeverity: ${d.severity}`;
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
            setTermMessages(prev => [...prev, { role: 'system', text: 'Commands:\n/help - this message\n/reset - reset simulation\n/status - system overview\n/shipment <id> - view detail\n/strategy <cost|speed|balanced>\n\nAgent commands:\n@Sentinel scan\n@Strategist:ETA_AGENT optimize shipment 13\n@Strategist:CARRIER_AGENT shipment 13\n@Actuary estimate cost impact\n@Cascade analyze risk\nApply option 1/2/3\n\nWhat have you learned so far?' }]);
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
                setTermMessages(prev => [...prev, { role: 'system', text: `[OK] Strategy set to: ${strat.toUpperCase()}` }]);
                await refresh();
                return;
            }
        }

        // Agent chat (via intent pipeline)
        try {
            // ── DETAILED AI THINKING CHAIN (DYNAMIC) ──
            const allThoughts = {
                Sentinel: { agent: 'Sentinel', role: 'Observer', text: 'Scanning Supabase telemetry stream... Analyzing risk signals across all active shipments. Checking disruption correlation matrices. Evaluating threshold: Risk > 0.7 triggers full agent mobilization.' },
                ETA_AGENT: { agent: 'ETA_AGENT', role: 'Physics Expert', text: 'Running XGBoost Regressor on distance, route complexity, current traffic density, and weather overlays. Ignoring carrier-reported ETAs. Computing Stryder Reality timestamps for all affected shipments.' },
                DELAY_AGENT: { agent: 'DELAY_AGENT', role: 'Risk Probability', text: 'LightGBM Classifier activated. Calculating statistical probability of SLA breach per shipment. Cross-referencing historical delay patterns with current conditions. Outputting breach probability percentages.' },
                CARRIER_AGENT: { agent: 'CARRIER_AGENT', role: 'Partner Auditor', text: 'Ridge Regression scoring carrier reliability in real-time. Analyzing historical delivery variance and recent port-specific performance. Generating carrier trust scores for the Strategist.' },
                HUB_AGENT: { agent: 'HUB_AGENT', role: 'Bottleneck Forecaster', text: 'Prophet/LSTM time-series model forecasting warehouse and port congestion. Scanning inbound volume vs throughput. Identifying potential Black Hole hubs approaching capacity limits.' },
                CASCADE_MODEL: { agent: 'CASCADE_MODEL', role: 'Impact Analyst', text: 'PyTorch MLP neural network aggregating all sub-agent outputs. Computing Blast Radius analysis — determining if failures will chain-react across shipment network. Generating final Stryder Risk Score (0-1).' },
                Strategist: { agent: 'Strategist', role: 'Reasoning', text: 'Synthesizing all sub-agent scores into actionable hypotheses. Weighing ETA predictions, delay probabilities, carrier reliability, hub congestion, and cascade risk. Formulating optimal response strategy.' },
                Actuary: { agent: 'Actuary', role: 'Decision', text: 'Performing cost-benefit analysis: SLA Penalty vs. Reroute Cost. Evaluating financial impact of each proposed intervention. Selecting economically optimal action plan.' },
                Executor: { agent: 'Executor', role: 'Action', text: 'Preparing API commands for dispatch. Queueing terminal map updates and shipment reroutes. Logging all fix operations for audit trail.' },
                System: { agent: 'System', role: 'Core', text: 'Parsing query intent. Translating natural language to internal routing protocols. Accessing current simulation state.' }
            };

            let involvedAgents = [];
            const lowerMsg = msg.toLowerCase();

            if (lowerMsg.includes('@sentinel') || lowerMsg.includes('scan') || lowerMsg.includes('monitor')) involvedAgents.push('Sentinel');
            if (lowerMsg.includes('eta_agent') || lowerMsg.includes('optimize') || lowerMsg.includes('eta')) involvedAgents.push('ETA_AGENT');
            if (lowerMsg.includes('delay_agent') || lowerMsg.includes('delay')) involvedAgents.push('DELAY_AGENT');
            if (lowerMsg.includes('carrier_agent') || lowerMsg.includes('carrier')) involvedAgents.push('CARRIER_AGENT');
            if (lowerMsg.includes('hub_agent') || lowerMsg.includes('hub')) involvedAgents.push('HUB_AGENT');
            if (lowerMsg.includes('cascade_model') || lowerMsg.includes('@cascade') || lowerMsg.includes('risk')) involvedAgents.push('CASCADE_MODEL');
            if (lowerMsg.includes('@strategist') || lowerMsg.includes('optimize') || lowerMsg.includes('reroute')) involvedAgents.push('Strategist');
            if (lowerMsg.includes('@actuary') || lowerMsg.includes('cost') || lowerMsg.includes('impact') || lowerMsg.includes('optimize') || lowerMsg.includes('estimate')) involvedAgents.push('Actuary');
            if (lowerMsg.includes('@executor') || lowerMsg.includes('apply') || lowerMsg.includes('fix') || lowerMsg.includes('optimize') || lowerMsg.includes('execute')) involvedAgents.push('Executor');

            const pipelineOrder = ['Sentinel', 'ETA_AGENT', 'DELAY_AGENT', 'CARRIER_AGENT', 'HUB_AGENT', 'CASCADE_MODEL', 'Strategist', 'Actuary', 'Executor'];

            let thinkingSteps = [];
            if (involvedAgents.length > 0) {
                involvedAgents = [...new Set(involvedAgents)];
                involvedAgents.sort((a, b) => pipelineOrder.indexOf(a) - pipelineOrder.indexOf(b));
                thinkingSteps = involvedAgents.map(name => allThoughts[name]);
            } else {
                thinkingSteps = [allThoughts.System];
            }

            // Push thinking animation message
            setTermMessages(prev => [...prev, { role: 'thinking-chain', steps: thinkingSteps, text: '' }]);

            // Artificial delay to let thinking animation play
            const delay = Math.floor(Math.random() * 2000) + 3000;
            await new Promise(r => setTimeout(r, delay));

            const r = await fetch(`${CHAT_API}/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
            const data = await r.json();

            // Replace thinking chain with finished result + store thought process
            const thoughtId = Date.now();
            setTermMessages(prev => {
                const f = prev.filter(m => m.role !== 'thinking-chain' && m.role !== 'thinking');
                return [...f, { role: 'agent', agent: data.agent, text: data.response, typing: true, thoughtId, thinkingSteps }];
            });
            setTimeout(() => {
                setTermMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, typing: false } : m));
            }, Math.min(3000, 400 + data.response.length * 5));
            await refresh();
        } catch (e) {
            setTermMessages(prev => prev.filter(m => m.role !== 'thinking-chain' && m.role !== 'thinking'));
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

    // Filter shipments for both map and CRM
    const allShipments = state?.shipments || [];
    const filteredShipments = useMemo(() => {
        return allShipments.filter(s => {
            if (crmFilters.status.length && !crmFilters.status.includes(s.status)) return false;
            if (crmFilters.carrier.length && !crmFilters.carrier.includes(s.carrier)) return false;
            if (crmFilters.origin.length && !crmFilters.origin.includes(s.origin)) return false;
            if (crmFilters.destination.length && !crmFilters.destination.includes(s.destination)) return false;
            return true;
        });
    }, [allShipments, crmFilters]);

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
                        <button className={`nav-tab ${view === 'learning-hub' ? 'active' : ''}`} onClick={() => setView('learning-hub')}>Learning Hub</button>
                    </div>
                </div>
                <div className="top-right">
                    {/* Strategy Mode Toggle */}
                    <div style={{
                        display: 'flex', gap: 2, padding: 3,
                        background: 'var(--glass-bg)', backdropFilter: 'blur(12px)',
                        border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-pill, 9999px)',
                    }}>
                        {['balanced', 'cost', 'speed'].map(s => (
                            <button key={s}
                                onClick={async () => { await post('/strategy', { strategy: s }); await refresh(); }}
                                style={{
                                    fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 700,
                                    padding: '6px 14px', border: 'none', borderRadius: 'var(--radius-pill, 9999px)',
                                    cursor: 'pointer', letterSpacing: 0.5, textTransform: 'uppercase',
                                    transition: 'all 0.25s ease',
                                    background: strategy === s ? 'rgba(0, 255, 135, 0.15)' : 'transparent',
                                    color: strategy === s ? '#00ff87' : 'var(--text-muted)',
                                    boxShadow: strategy === s ? '0 0 12px rgba(0, 255, 135, 0.2)' : 'none',
                                }}
                            >
                                {s === 'balanced' ? 'Balanced' : s === 'cost' ? 'Cost' : 'Speed'}
                            </button>
                        ))}
                    </div>

                    <span className="sep">│</span>

                    <button className={`tb ${loading === 'agents' ? 'loading' : ''}`} onClick={handleRunAgents}>Run Agents</button>
                    <button className={`tb tb-mode ${autoMode ? 'auto' : 'manual'}`} onClick={handleToggleMode}>MODE: {autoMode ? 'AUTO' : 'MANUAL'}</button>
                </div>
            </div>

            {view === 'terminal' ? (
                <div className="main-grid">
                    <div className="left-col">
                        <div className="map-container" style={{ position: 'relative' }}>
                            <OpsMap
                                simTime={simTime}
                                shipments={filteredShipments}
                                ports={state?.ports || []}
                                warehouses={state?.warehouses || []}
                                onSelectShipment={setSelectedShipment}
                                onPortClick={p => setPortDetail(p)}
                                onWhClick={w => setWhDetail(w)}
                                theme={mapTheme}
                            />

                            {/* Control Panel Toggle */}
                            <button
                                onClick={() => setShowControlPanel(!showControlPanel)}
                                style={{
                                    position: 'absolute', top: 12, right: 12, zIndex: 1000,
                                    background: showControlPanel ? 'rgba(0, 255, 135, 0.1)' : 'rgba(10,10,10,0.8)',
                                    backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
                                    border: showControlPanel ? '1px solid var(--accent)' : '1px solid var(--glass-border)',
                                    borderRadius: 'var(--radius)',
                                    color: showControlPanel ? 'var(--white)' : 'var(--text)',
                                    fontFamily: 'var(--font-display)', fontSize: 11,
                                    fontWeight: 700, padding: '8px 14px', cursor: 'pointer',
                                    boxShadow: showControlPanel ? '0 0 12px rgba(0,255,135,0.2)' : '0 4px 12px rgba(0,0,0,0.5)',
                                    letterSpacing: 1, transition: 'all 0.2s', textTransform: 'uppercase'
                                }}
                            >
                                CONTROL PANEL {showControlPanel ? '^' : 'v'}
                            </button>

                            {/* Control Panel Dropdown */}
                            {showControlPanel && (
                                <div style={{
                                    position: 'absolute', top: 50, right: 12, zIndex: 1000,
                                    background: 'rgba(15,15,15,0.85)', backdropFilter: 'blur(20px)',
                                    WebkitBackdropFilter: 'blur(20px)',
                                    border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-card)',
                                    padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px',
                                    boxShadow: '0 16px 40px rgba(0,0,0,0.8)', minWidth: '240px',
                                    animation: 'fadeIn 0.2s var(--ease-out-expo)'
                                }}>

                                    {/* Map Theme Toggle */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                        <span className="sc-label">MAP THEME</span>
                                        <button className="sc-btn" onClick={() => setMapTheme(t => t === 'dark' ? 'light' : 'dark')} style={{ width: 90, padding: '4px 8px', fontSize: 10 }}>
                                            {mapTheme.toUpperCase()}
                                        </button>
                                    </div>

                                    {/* Playback Controls */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6, background: 'rgba(255,255,255,0.03)', padding: 6, borderRadius: 'var(--radius)', border: '1px solid var(--glass-border)' }}>
                                        <button className={`sc-btn ${simPaused ? 'paused' : ''}`} onClick={handlePause} title={simPaused ? 'Resume Sim' : 'Pause Sim'}>
                                            {simPaused ? '[Play]' : '[Pause]'}
                                        </button>
                                        <button className="sc-btn" onClick={handleStepTick} title="Step +1 Tick">+1</button>
                                        <button className={`sc-btn ${simFrozen ? 'frozen' : ''}`} onClick={handleFreeze} title={simFrozen ? 'Unfreeze' : 'Freeze State'}>
                                            {simFrozen ? '[Unfreeze]' : '[Freeze]'}
                                        </button>
                                        <button className="sc-btn" onClick={handleReset} title="Reset Simulation" style={{ color: 'var(--text-muted)' }}>[Reset]</button>
                                    </div>

                                    {/* Selectors */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span className="sc-label">SPEED</span>
                                            <select className="sc-select" value={simSpeed} onChange={e => handleSpeedChange(parseFloat(e.target.value))} style={{ width: 90, padding: '4px 8px' }}>
                                                <option value="0.25">0.25×</option>
                                                <option value="0.5">0.5×</option>
                                                <option value="1">1×</option>
                                                <option value="2">2×</option>
                                                <option value="5">5×</option>
                                            </select>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span className="sc-label">MOVEMENT</span>
                                            <select className="sc-select" value={moveScale} onChange={e => handleMoveScaleChange(parseFloat(e.target.value))} style={{ width: 90, padding: '4px 8px' }}>
                                                <option value="0">0%</option>
                                                <option value="0.25">25%</option>
                                                <option value="0.5">50%</option>
                                                <option value="1">100%</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div style={{ height: 1, background: 'var(--glass-border)', margin: '2px 0' }}></div>

                                    {/* Action Buttons */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        <div className="scenario-wrap" style={{ width: '100%' }}>
                                            <button className={`tb tb-scenario ${loading === 'scenario' || loading === 'disrupt' ? 'loading' : ''}`} onClick={() => setScenarioOpen(!scenarioOpen)} style={{ width: '100%', display: 'flex', justifyContent: 'center', padding: '8px' }}>Select Scenario ▾</button>
                                            {scenarioOpen && (
                                                <div className="scenario-dropdown" style={{ width: '100%', left: 0, right: 'auto', top: '100%', marginTop: 4 }}>
                                                    <button className="scenario-item" onClick={() => { setScenarioOpen(false); handleDisrupt(); }}>
                                                        <span className="sev-dot" style={{ background: 'var(--accent)', boxShadow: '0 0 6px var(--accent-muted)' }}></span>
                                                        Random Event
                                                    </button>
                                                    <div style={{ height: 1, background: 'var(--glass-border)', margin: '4px 0' }}></div>
                                                    {SCENARIOS.map(s => (
                                                        <button key={s.type} className="scenario-item" onClick={() => handleScenario(s.type)}>
                                                            <span className={`sev-dot sev-${s.severity.toLowerCase()}`}></span>
                                                            {s.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                        <div className="crm-container">
                            <CRMTable shipments={allShipments} onSelectShipment={setSelectedShipment} filters={crmFilters} onFiltersChange={setCrmFilters} />
                        </div>
                    </div>
                    <div className="right-col">
                        <div className="terminal-container" style={{ flex: 1 }}>
                            <AgentTerminal messages={termMessages} onSend={handleChat} onShipmentClick={handleShipmentClick} />
                        </div>
                    </div>
                </div>
            ) : view === 'dashboard' ? (
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
            ) : (
                <div className="learning-hub-view" style={{ flex: 1, overflowY: 'auto' }}>
                    <AgentsLearningHub />
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
                            <span>{portDetail.name}</span>
                            <button className="modal-close" onClick={() => setPortDetail(null)}>X</button>
                        </div>
                        <div className="modal-body" style={{ fontFamily: 'var(--font-body)', fontSize: 12 }}>
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
                            <span>{whDetail.name}</span>
                            <button className="modal-close" onClick={() => setWhDetail(null)}>X</button>
                        </div>
                        <div className="modal-body" style={{ fontFamily: 'var(--font-body)', fontSize: 12 }}>
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
