import { useEffect, useRef } from 'react';

/**
 * MetricsFeed — Live scrolling feed showing disruption/agent events.
 */
export default function MetricsFeed({ entries }) {
    const endRef = useRef(null);
    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [entries]);

    const typeColor = (t) => {
        if (t === 'disruption') return '#ef4444';
        if (t === 'warning') return '#f59e0b';
        if (t === 'agent') return '#22c55e';
        return '#666';
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#161616', overflow: 'hidden' }}>
            <div style={{
                padding: '6px 14px', borderBottom: '1px solid #2a2a2a', flexShrink: 0,
                fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, color: '#888',
                letterSpacing: 1, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8,
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b' }}></span>
                Metrics Feed
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '4px 12px' }}>
                {entries.length === 0 && (
                    <div style={{ padding: 20, textAlign: 'center', color: '#555', fontFamily: 'var(--font-body)', fontSize: 12 }}>
                        No events yet. Inject a disruption to see agent activity.
                    </div>
                )}
                {entries.map((e, i) => (
                    <div key={i} style={{
                        fontFamily: 'var(--font-body)', fontSize: 11, padding: '3px 0',
                        color: typeColor(e.type), display: 'flex', gap: 8, lineHeight: 1.5,
                    }}>
                        <span style={{ color: '#555', flexShrink: 0 }}>[{e.ts}]</span>
                        <span>{e.msg}</span>
                    </div>
                ))}
                <div ref={endRef} />
            </div>
        </div>
    );
}
