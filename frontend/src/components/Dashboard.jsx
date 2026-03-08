/**
 * Dashboard v4 — Three horizontal sections (Left, Center, Right):
 * Left: CASCADE INTELLIGENCE CENTER (predictions + historical alerts)
 * Center: AGENT LEARNING LOGS (chronological, not grouped by agent)
 * Right: AGENT REPLAY SYSTEM (past events with step-by-step replay + map animation)
 * 
 * Aesthetic: Cinematic Futurist, Glassmorphism, Syne headers, Inter body, Green/White theme.
 */
import { useState, useEffect } from 'react';

function AnimatedNumber({ value, prefix = '', suffix = '', duration = 1500 }) {
    const [count, setCount] = useState(0);

    useEffect(() => {
        let startTimestamp = null;
        let animationFrameId;

        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            setCount(easeProgress * value);

            if (progress < 1) {
                animationFrameId = window.requestAnimationFrame(step);
            }
        };
        animationFrameId = window.requestAnimationFrame(step);

        return () => window.cancelAnimationFrame(animationFrameId);
    }, [value, duration]);

    const displayValue = count.toLocaleString(undefined, {
        maximumFractionDigits: Number.isInteger(value) ? 0 : 1,
        minimumFractionDigits: Number.isInteger(value) ? 0 : 1
    });

    return <span>{prefix}{displayValue}{suffix}</span>;
}

// Unified agent colors strictly bounded to our aesthetic (shades of dark, glass, emerald, cyan, white)
const AGENT_COLORS = {
    Sentinel: '#ffffff', Strategist: '#00ff87', Actuary: '#60efff',
    Executor: '#1fb96a', Cascade: '#ffffff', System: '#00ff87',
};

export default function Dashboard({ agentStats, agentMemory, eventLog, cascadeAlerts, learningLogs, scenarioHistory, onCascadeFix }) {
    const [replayEvent, setReplayEvent] = useState(null);
    const [expandedLog, setExpandedLog] = useState(null);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => setLoaded(true), 50);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div style={{
            width: '100%', minHeight: '100%', display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(350px, 1.5fr) minmax(300px, 1fr)', gap: 32, padding: '32px',
            opacity: loaded ? 1 : 0, transform: loaded ? 'translateY(0)' : 'translateY(30px)', transition: 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>

            {/* ════════ LEFT: CASCADE INTELLIGENCE CENTER ════════ */}
            <Section title="CASCADE INTELLIGENCE CENTER" icon="//" count={cascadeAlerts.length}>
                {/* Active predictions */}
                {cascadeAlerts.length === 0
                    ? <Empty text="No cascade risks detected. System stable." />
                    : cascadeAlerts.map((a, i) => (
                        <div key={i} className="dashboard-card" style={{ marginBottom: 12 }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 14, color: '#e0e0e0', marginBottom: 8 }}>
                                    Predicted: {a.location}
                                    <span style={{
                                        marginLeft: 8, fontSize: 10, padding: '2px 6px', borderRadius: 4,
                                        background: 'rgba(255, 255, 255, 0.1)', color: 'var(--accent)', fontWeight: 700, fontFamily: 'var(--font-sans)'
                                    }}><AnimatedNumber value={a.confidence} suffix="% confidence" /></span>
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, fontFamily: 'var(--font-sans)' }}>
                                    {a.type.replace(/_/g, ' ').toUpperCase()}<br />
                                    <span style={{ color: 'var(--text-muted)' }}><AnimatedNumber value={a.impact_count} suffix=" shipments at risk" /></span><br />
                                    Suggestion: <span style={{ color: 'var(--accent)' }}>{a.suggestion}</span>
                                </div>
                            </div>
                            <div style={{ marginTop: 12, textAlign: 'right' }}>
                                <button onClick={() => onCascadeFix?.(a)} className="glass-btn" style={{ padding: '6px 16px', fontSize: 11 }}>
                                    FIX RESOLUTION →
                                </button>
                            </div>
                        </div>
                    ))
                }

                {/* Scenario history */}
                {scenarioHistory?.length > 0 && (
                    <div style={{ marginTop: 24 }}>
                        <div style={{ fontFamily: 'var(--font-display)', fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: 1, marginBottom: 12 }}>SCENARIO HISTORY</div>
                        {scenarioHistory.map((s, i) => (
                            <div key={i} className="dashboard-card-mini" style={{ marginBottom: 8, display: 'flex', gap: 12, justifyContent: 'space-between', fontSize: 11, fontFamily: 'var(--font-sans)' }}>
                                <span style={{ color: 'var(--text-secondary)' }}>{s.description}</span>
                                <span style={{ color: 'var(--text-muted)' }}>{s.location}</span>
                            </div>
                        ))}
                    </div>
                )}
            </Section>

            {/* ════════ CENTER: AGENT LEARNING LOGS ════════ */}
            <Section title="AGENT LEARNING LOGS" icon="//" count={learningLogs.length}>
                {/* Cumulative stats row */}
                <div style={{ display: 'flex', gap: 16, padding: '16px', background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))', borderRadius: 'var(--radius)', border: '1px solid var(--glass-border)', marginBottom: 24 }}>
                    <Stat label="Hours Saved" value={agentMemory.total_hours_saved || 0} suffix="h" />
                    <Stat label="Cost Saved" value={agentMemory.total_cost_saved || 0} prefix="$" />
                    <Stat label="Optimizations" value={agentMemory.optimizations || 0} />
                </div>

                {/* Agent stats cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
                    {Object.entries(agentStats).map(([name, data]) => (
                        <div key={name} className="dashboard-card-mini">
                            <div style={{ fontFamily: 'var(--font-sans)', fontStyle: 'italic', fontWeight: 800, fontSize: 15, color: 'var(--text-primary)', letterSpacing: 1, marginBottom: 8 }}>{name}</div>
                            {Object.entries(data).map(([k, v]) => (
                                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, padding: '2px 0', color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' }}>
                                    <span>{k.replace(/_/g, ' ')}</span>
                                    <span style={{ color: 'var(--text)', fontWeight: 600 }}>
                                        {typeof v === 'number' ? (
                                            <AnimatedNumber value={v} suffix={k.includes('rate') || k.includes('accuracy') || k.includes('error') ? '%' : ''} />
                                        ) : v || '—'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ))}
                </div>

                {/* Chronological learning logs */}
                <div style={{ flex: 1, minHeight: 400, overflowY: 'auto', borderRadius: 'var(--radius)', border: '1px solid var(--glass-border)' }} className="custom-scroll">
                    {learningLogs.length === 0
                        ? <Empty text="No learnings yet. Interact with agents to generate learning logs." />
                        : [...learningLogs].reverse().map((log, i) => (
                            <div key={log.id || i}
                                onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                                className="dashboard-log-item"
                                style={{
                                    padding: '24px 24px', borderBottom: '1px solid var(--glass-border)',
                                    background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)',
                                    cursor: 'pointer', transition: 'background .2s',
                                    display: 'flex', alignItems: 'flex-start', gap: 16,
                                }}
                            >
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 2 }}>[{log.ts}]</span>
                                <span style={{
                                    fontFamily: 'var(--font-sans)', fontStyle: 'italic', fontSize: 16, fontWeight: 800,
                                    color: 'var(--text-primary)',
                                    minWidth: 80, whiteSpace: 'nowrap',
                                }}>{log.agent}</span>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 15, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{log.message}</span>
                            </div>
                        ))
                    }
                </div>
            </Section>

            {/* ════════ RIGHT: AGENT REPLAY SYSTEM ════════ */}
            <Section title="AGENT REPLAY SYSTEM" icon="//" count={eventLog.length}>
                {eventLog.length === 0
                    ? <Empty text="No events yet. Inject disruptions to generate events for replay." />
                    : eventLog.map(ev => (
                        <div key={ev.id} onClick={() => setReplayEvent(ev)} className="dashboard-card" style={{ marginBottom: 12, cursor: 'pointer' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                <span style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 800, color: 'var(--text-primary)' }}>{ev.title}</span>
                                <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: 'rgba(0, 255, 135, 0.1)', color: 'var(--accent)', fontWeight: 700, fontFamily: 'var(--font-sans)', border: '1px solid var(--glass-border)' }}>RESOLVED</span>
                            </div>
                            <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>{ev.summary}</div>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 12 }}>{ev.cost_impact} • Click to replay →</div>
                        </div>
                    ))
                }
            </Section>

            {/* ──── Replay Modal ──── */}
            {replayEvent && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.85)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    onClick={() => setReplayEvent(null)}>
                    <div className="dashboard-card" style={{ maxWidth: 720, width: '90%', maxHeight: '85vh', display: 'flex', flexDirection: 'column', p: 0, padding: 0 }}
                        onClick={e => e.stopPropagation()}>
                        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>
                                [Replay]: {replayEvent.title}
                            </span>
                            <button onClick={() => setReplayEvent(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 18, cursor: 'pointer' }}>X</button>
                        </div>
                        <div style={{ padding: 24, overflowY: 'auto', flex: 1 }} className="custom-scroll">
                            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--glass-border)', fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' }}>
                                <span>Severity: <b style={{ color: 'var(--accent)' }}>{replayEvent.severity}</b></span>
                                <span>Affected: <AnimatedNumber value={replayEvent.affected_count} /></span>
                                <span>Rerouted: <AnimatedNumber value={replayEvent.rerouted_count} /></span>
                                <span>{replayEvent.cost_impact}</span>
                                <span style={{ color: 'var(--accent)', fontWeight: 700, marginLeft: 'auto' }}>[RESOLVED]</span>
                            </div>

                            {/* Step-by-step replay */}
                            {replayEvent.steps?.map((step, i) => (
                                <div key={i} style={{ padding: '12px 0', position: 'relative' }}>
                                    {i < replayEvent.steps.length - 1 && (
                                        <div style={{ position: 'absolute', left: 42, top: 32, bottom: -12, width: 1, background: 'var(--glass-border)' }}></div>
                                    )}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                        <span style={{ width: 24, height: 24, borderRadius: '50%', background: 'rgba(255,255,255,0.05)', border: `1px solid ${AGENT_COLORS[step.agent] || 'var(--accent)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: AGENT_COLORS[step.agent] || 'var(--text)', fontWeight: 700, flexShrink: 0, fontFamily: 'var(--font-mono)' }}>
                                            {i + 1}
                                        </span>
                                        <span style={{ fontFamily: 'var(--font-sans)', fontStyle: 'italic', fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: 1 }}>{step.agent}</span>
                                    </div>
                                    <div style={{ lineHeight: 1.7, color: 'var(--text-secondary)', paddingLeft: 40, fontSize: 13, fontFamily: 'var(--font-sans)' }}>
                                        {step.bullets?.map((b, j) => <div key={j}>• {b}</div>)}
                                    </div>
                                </div>
                            ))}

                            {/* Fix details */}
                            {replayEvent.fix_details?.length > 0 && (
                                <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--glass-border)' }}>
                                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 12 }}>Fix Details</div>
                                    {replayEvent.fix_details.map((f, i) => (
                                        <div key={i} style={{ display: 'flex', gap: 16, padding: '8px 0', fontSize: 12, color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.05)', alignItems: 'center', fontFamily: 'var(--font-sans)' }}>
                                            <span style={{ color: 'var(--white)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>#{f.id}</span>
                                            <span>{f.old_carrier} → {f.new_carrier}</span>
                                            <span>ETA: {f.old_eta}h → {f.new_eta}h</span>
                                            <span style={{ color: 'var(--text-muted)' }}>${f.old_cost?.toLocaleString()} → ${f.new_cost?.toLocaleString()}</span>
                                            <span style={{ color: 'var(--accent)', marginLeft: 'auto', fontWeight: 600 }}>{f.fix}</span>
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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{
                fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800,
                marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12,
                borderBottom: '1px solid var(--glass-border)', paddingBottom: 16,
            }}>
                <span style={{ fontSize: 20, color: 'var(--accent)' }}>{icon}</span>
                <span style={{
                    background: 'linear-gradient(180deg, #ffffff 40%, #00ff87 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                }}>{title}</span>
            </div>
            {children}
        </div>
    );
}

function Stat({ label, value, prefix = '', suffix = '' }) {
    return (
        <div style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>
                {typeof value === 'number' ? <AnimatedNumber value={value} prefix={prefix} suffix={suffix ? <span style={{ color: 'var(--accent)', fontSize: '0.8em' }}>{suffix}</span> : ''} /> : value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 4, letterSpacing: 1, textTransform: 'uppercase', fontFamily: 'var(--font-sans)' }}>{label}</div>
        </div>
    );
}

function Empty({ text }) {
    return (
        <div style={{ padding: 32, textAlign: 'center', fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--text-muted)' }}>{text}</div>
    );
}
