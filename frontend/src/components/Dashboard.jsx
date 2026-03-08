/**
 * Dashboard v3 — Three vertical sections:
 * 1. AGENT LEARNING LOGS (chronological, not grouped by agent)
 * 2. CASCADE INTELLIGENCE CENTER (predictions + historical alerts)
 * 3. AGENT REPLAY SYSTEM (past events with step-by-step replay + map animation)
 */
import { useState } from 'react';

const AGENT_COLORS = {
    Sentinel: '#ef4444', Strategist: '#8b5cf6', Actuary: '#f59e0b',
    Executor: '#22c55e', Cascade: '#06b6d4', System: '#8b5cf6',
};

export default function Dashboard({ agentStats, agentMemory, eventLog, cascadeAlerts, learningLogs, scenarioHistory, onCascadeFix }) {
    const [replayEvent, setReplayEvent] = useState(null);
    const [expandedLog, setExpandedLog] = useState(null);

    return (
        <div style={{ maxWidth: 960, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* ════════ SECTION 1: AGENT LEARNING LOGS ════════ */}
            <Section title="AGENT LEARNING LOGS" icon="📋" color="#8b5cf6" count={learningLogs.length}>
                {/* Cumulative stats row */}
                <div style={{ display: 'flex', gap: 16, padding: '12px 16px', background: '#161616', borderRadius: 6, border: '1px solid #222', marginBottom: 12 }}>
                    <Stat label="Hours Saved" value={agentMemory.total_hours_saved || 0} suffix="h" color="#22c55e" />
                    <Stat label="Cost Saved" value={`₹${(agentMemory.total_cost_saved || 0).toLocaleString()}`} color="#3b82f6" />
                    <Stat label="Optimizations" value={agentMemory.optimizations || 0} color="#8b5cf6" />
                    <Stat label="Strategy" value={(agentMemory.strategy || 'balanced').toUpperCase()} color="#f59e0b" />
                </div>

                {/* Agent stats cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 8, marginBottom: 16 }}>
                    {Object.entries(agentStats).map(([name, data]) => (
                        <div key={name} style={{
                            padding: '10px 12px', background: '#1a1a1a', borderRadius: 6,
                            border: '1px solid #2a2a2a', borderTop: `2px solid ${AGENT_COLORS[name] || '#555'}`,
                        }}>
                            <div style={{ fontWeight: 700, fontSize: 10, color: AGENT_COLORS[name] || '#888', letterSpacing: 1, marginBottom: 6 }}>{name}</div>
                            {Object.entries(data).map(([k, v]) => (
                                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, padding: '1px 0', color: '#888' }}>
                                    <span>{k.replace(/_/g, ' ')}</span>
                                    <span style={{ color: '#ccc', fontWeight: 600 }}>
                                        {typeof v === 'number' ? (k.includes('rate') || k.includes('accuracy') || k.includes('error') ? `${v}%` : v.toLocaleString()) : v || '—'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>

                {/* Chronological learning logs */}
                <div style={{ maxHeight: 300, overflowY: 'auto', borderRadius: 6, border: '1px solid #222' }}>
                    {learningLogs.length === 0
                        ? <Empty text="No learnings yet. Interact with agents to generate learning logs." />
                        : [...learningLogs].reverse().map((log, i) => (
                            <div key={log.id || i}
                                onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                                style={{
                                    padding: '8px 14px', borderBottom: '1px solid #1a1a1a',
                                    background: i % 2 === 0 ? '#161616' : '#1a1a1a',
                                    cursor: 'pointer', transition: 'background .1s',
                                    display: 'flex', alignItems: 'flex-start', gap: 10,
                                }}
                                onMouseEnter={e => e.currentTarget.style.background = '#222'}
                                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#161616' : '#1a1a1a'}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#555', whiteSpace: 'nowrap', marginTop: 1 }}>[{log.ts}]</span>
                                <span style={{
                                    fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                                    color: AGENT_COLORS[log.agent] || '#888', minWidth: 70, whiteSpace: 'nowrap',
                                }}>{log.agent}</span>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#ccc', lineHeight: 1.4 }}>{log.message}</span>
                            </div>
                        ))
                    }
                </div>
            </Section>

            {/* ════════ SECTION 2: CASCADE INTELLIGENCE CENTER ════════ */}
            <Section title="CASCADE INTELLIGENCE CENTER" icon="⚠" color="#f59e0b" count={cascadeAlerts.length}>
                {/* Active predictions */}
                {cascadeAlerts.length === 0
                    ? <Empty text="No cascade risks detected. System stable." />
                    : cascadeAlerts.map((a, i) => (
                        <div key={i} style={{
                            padding: '14px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
                            borderLeft: `3px solid ${a.confidence > 70 ? '#ef4444' : '#f59e0b'}`,
                            borderRadius: 6, marginBottom: 8, display: 'flex', alignItems: 'flex-start', gap: 16,
                        }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 700, fontSize: 12, color: '#e0e0e0', marginBottom: 4 }}>
                                    Predicted: {a.location}
                                    <span style={{
                                        marginLeft: 8, fontSize: 9, padding: '1px 6px', borderRadius: 3,
                                        background: a.confidence > 75 ? '#ef444418' : '#f59e0b18',
                                        color: a.confidence > 75 ? '#ef4444' : '#f59e0b', fontWeight: 700,
                                    }}>{a.confidence}% confidence</span>
                                </div>
                                <div style={{ fontSize: 11, color: '#888', lineHeight: 1.6 }}>
                                    {a.type.replace(/_/g, ' ').toUpperCase()}<br />
                                    {a.impact_count} shipments at risk<br />
                                    Suggestion: {a.suggestion}
                                </div>
                            </div>
                            <button onClick={() => onCascadeFix?.(a)} style={{
                                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                                padding: '8px 16px', background: '#22c55e11', border: '1px solid #22c55e44',
                                borderRadius: 4, color: '#22c55e', cursor: 'pointer', whiteSpace: 'nowrap',
                            }}>FIX →</button>
                        </div>
                    ))
                }

                {/* Scenario history */}
                {scenarioHistory?.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: '#666', letterSpacing: 1, marginBottom: 8 }}>SCENARIO HISTORY</div>
                        {scenarioHistory.map((s, i) => (
                            <div key={i} style={{ padding: '8px 14px', background: '#161616', borderRadius: 4, marginBottom: 4, borderLeft: '2px solid #f59e0b44', display: 'flex', gap: 12, justifyContent: 'space-between', fontSize: 10, fontFamily: 'var(--font-mono)', color: '#888' }}>
                                <span style={{ color: '#ccc' }}>{s.description}</span>
                                <span>{s.location}</span>
                                <span>{s.affected_count} affected</span>
                            </div>
                        ))}
                    </div>
                )}
            </Section>

            {/* ════════ SECTION 3: AGENT REPLAY SYSTEM ════════ */}
            <Section title="AGENT REPLAY SYSTEM" icon="↻" color="#06b6d4" count={eventLog.length}>
                {eventLog.length === 0
                    ? <Empty text="No events yet. Inject disruptions to generate events for replay." />
                    : eventLog.map(ev => (
                        <div key={ev.id} onClick={() => setReplayEvent(ev)} style={{
                            padding: '12px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
                            borderRadius: 6, cursor: 'pointer', marginBottom: 6, transition: 'all .15s',
                            borderLeft: `3px solid ${ev.severity === 'HIGH' ? '#ef4444' : ev.severity === 'MEDIUM' ? '#f59e0b' : '#22c55e'}`,
                        }}
                            onMouseEnter={e => { e.currentTarget.style.background = '#222'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = '#1a1a1a'; }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontSize: 12, fontWeight: 700, color: '#e0e0e0' }}>{ev.title}</span>
                                <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, background: '#22c55e18', color: '#22c55e', fontWeight: 700 }}>RESOLVED</span>
                            </div>
                            <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{ev.summary}</div>
                            <div style={{ fontSize: 10, color: '#555', marginTop: 2 }}>{ev.cost_impact} • Click to replay →</div>
                        </div>
                    ))
                }
            </Section>

            {/* ──── Replay Modal ──── */}
            {replayEvent && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.75)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    onClick={() => setReplayEvent(null)}>
                    <div style={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8, maxWidth: 640, width: '90%', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}
                        onClick={e => e.stopPropagation()}>
                        <div style={{ padding: '12px 16px', borderBottom: '1px solid #333', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: '#fff' }}>
                            <span>↻ Replay: {replayEvent.title}</span>
                            <button onClick={() => setReplayEvent(null)} style={{ background: 'none', border: 'none', color: '#888', fontSize: 16, cursor: 'pointer' }}>✕</button>
                        </div>
                        <div style={{ padding: 16, overflowY: 'auto', flex: 1, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                            {/* Timeline header */}
                            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid #333', fontSize: 11, color: '#888' }}>
                                <span>Severity: <b style={{ color: replayEvent.severity === 'HIGH' ? '#ef4444' : '#f59e0b' }}>{replayEvent.severity}</b></span>
                                <span>Affected: {replayEvent.affected_count}</span>
                                <span>Rerouted: {replayEvent.rerouted_count}</span>
                                <span>{replayEvent.cost_impact}</span>
                                <span style={{ color: '#22c55e', fontWeight: 700, marginLeft: 'auto' }}>✓ RESOLVED</span>
                            </div>

                            {/* Step-by-step replay */}
                            {replayEvent.steps?.map((step, i) => (
                                <div key={i} style={{ padding: '10px 0', position: 'relative' }}>
                                    {i < replayEvent.steps.length - 1 && (
                                        <div style={{ position: 'absolute', left: 38, top: 26, bottom: -10, width: 1, background: '#333' }}></div>
                                    )}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                        <span style={{ width: 20, height: 20, borderRadius: '50%', background: `${AGENT_COLORS[step.agent] || '#555'}22`, border: `2px solid ${AGENT_COLORS[step.agent] || '#555'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, color: AGENT_COLORS[step.agent], fontWeight: 700, flexShrink: 0 }}>
                                            {i + 1}
                                        </span>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: AGENT_COLORS[step.agent] || '#888', letterSpacing: 1 }}>{step.agent}</span>
                                    </div>
                                    <div style={{ lineHeight: 1.7, color: '#d0d0d0', paddingLeft: 32, fontSize: 11 }}>
                                        {step.bullets?.map((b, j) => <div key={j}>• {b}</div>)}
                                    </div>
                                </div>
                            ))}

                            {/* Fix details */}
                            {replayEvent.fix_details?.length > 0 && (
                                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #333' }}>
                                    <div style={{ fontSize: 10, fontWeight: 700, color: '#888', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>Fix Details</div>
                                    {replayEvent.fix_details.map((f, i) => (
                                        <div key={i} style={{ display: 'flex', gap: 12, padding: '5px 0', fontSize: 11, color: '#999', borderBottom: '1px solid #222', alignItems: 'center' }}>
                                            <span style={{ color: '#3b82f6', fontWeight: 700 }}>#{f.id}</span>
                                            <span>{f.old_carrier} → {f.new_carrier}</span>
                                            <span>ETA: {f.old_eta}h → {f.new_eta}h</span>
                                            <span style={{ color: '#888' }}>₹{f.old_cost?.toLocaleString()} → ₹{f.new_cost?.toLocaleString()}</span>
                                            <span style={{ color: '#22c55e', marginLeft: 'auto' }}>{f.fix}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function Section({ title, icon, color, count, children }) {
    return (
        <div>
            <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: '#888',
                letterSpacing: 1, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8,
                borderBottom: '1px solid #222', paddingBottom: 8,
            }}>
                <span style={{ fontSize: 14 }}>{icon}</span>
                <span>{title}</span>
                {count != null && <span style={{ color, fontWeight: 700 }}>({count})</span>}
            </div>
            {children}
        </div>
    );
}

function Stat({ label, value, suffix, color }) {
    return (
        <div style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>{value}{suffix || ''}</div>
            <div style={{ fontSize: 8, color: '#888', marginTop: 2, letterSpacing: 1, textTransform: 'uppercase' }}>{label}</div>
        </div>
    );
}

function Empty({ text }) {
    return (
        <div style={{ padding: 24, textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, color: '#555' }}>{text}</div>
    );
}
