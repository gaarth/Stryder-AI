/**
 * EventLog — Dashboard view. Shows unified event log (not per-agent).
 * Each event is clickable for full replay.
 */
export default function EventLog({ events, onReplay }) {
    if (!events || events.length === 0) {
        return (
            <div style={{ padding: 40, textAlign: 'center', fontFamily: 'var(--font-mono)', color: '#555' }}>
                <div style={{ fontSize: 24, marginBottom: 12 }}>⬡</div>
                <div style={{ fontSize: 13 }}>No events yet</div>
                <div style={{ fontSize: 11, color: '#444', marginTop: 4 }}>Switch to Terminal and inject disruptions to generate events.</div>
            </div>
        );
    }

    const sevColor = (s) => s === 'HIGH' ? '#ef4444' : s === 'MEDIUM' ? '#f59e0b' : '#22c55e';

    return (
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
            <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: '#888',
                letterSpacing: 1, textTransform: 'uppercase', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8,
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b' }}></span>
                Event History — {events.length} events
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {events.map(ev => (
                    <div key={ev.id} onClick={() => onReplay?.(ev)} style={{
                        padding: '14px 16px', background: '#1a1a1a', border: '1px solid #2a2a2a',
                        borderRadius: 6, cursor: 'pointer', transition: 'all .15s',
                        borderLeft: `3px solid ${sevColor(ev.severity)}`,
                    }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#222'; e.currentTarget.style.borderColor = '#444'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = '#1a1a1a'; e.currentTarget.style.borderColor = '#2a2a2a'; }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: '#e0e0e0' }}>{ev.title}</span>
                            <span style={{
                                fontSize: 9, fontWeight: 700, padding: '1px 8px', borderRadius: 3,
                                background: `${sevColor(ev.severity)}18`, color: sevColor(ev.severity),
                            }}>{ev.severity}</span>
                            <span style={{ marginLeft: 'auto', fontSize: 10, color: '#22c55e', fontWeight: 700 }}>✓ RESOLVED</span>
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#999', lineHeight: 1.5 }}>
                            {ev.summary}
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#555', marginTop: 4 }}>
                            Click to view full agent replay →
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
