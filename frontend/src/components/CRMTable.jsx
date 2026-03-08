import { useState } from 'react';

export default function CRMTable({ shipments, onSelectShipment }) {
    const [sortBy, setSortBy] = useState('id');
    const [sortDir, setSortDir] = useState(1);

    const sorted = [...shipments].sort((a, b) => {
        if (sortBy === 'id') return (a.id - b.id) * sortDir;
        if (sortBy === 'status') return a.status.localeCompare(b.status) * sortDir;
        if (sortBy === 'eta') return (a.eta_hours - b.eta_hours) * sortDir;
        if (sortBy === 'cost') return ((a.current_cost || 0) - (b.current_cost || 0)) * sortDir;
        return 0;
    });

    const toggleSort = (col) => {
        if (sortBy === col) setSortDir(d => d * -1);
        else { setSortBy(col); setSortDir(1); }
    };

    const sc = (s) => s === 'DELAYED' ? '#ef4444' : s === 'AT_RISK' ? '#f59e0b' : s === 'DELIVERED' ? '#22c55e' : '#3b82f6';

    const COLS = [
        { key: 'id', label: '#', w: 32 },
        { key: 'origin', label: 'Origin' },
        { key: 'dest', label: 'Dest' },
        { key: 'carrier', label: 'Carrier' },
        { key: 'status', label: 'Status', w: 72 },
        { key: 'eta', label: 'ETA', w: 48 },
        { key: 'cost', label: 'Cost', w: 72 },
        { key: 'upd', label: '', w: 24 },
    ];

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#1a1a1a', overflow: 'hidden' }}>
            <div style={{
                padding: '6px 14px', borderBottom: '1px solid #2a2a2a', flexShrink: 0,
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: '#888',
                letterSpacing: 1, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8,
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6' }}></span>
                CRM
                <span style={{ marginLeft: 'auto', color: '#555' }}>{shipments.length}</span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                    <thead>
                        <tr style={{ position: 'sticky', top: 0, background: '#222', zIndex: 1 }}>
                            {COLS.map(h => (
                                <th key={h.key} onClick={() => h.key !== 'upd' && toggleSort(h.key)} style={{
                                    padding: '5px 6px', textAlign: 'left', borderBottom: '1px solid #333',
                                    fontSize: 9, fontWeight: 700, color: '#888', letterSpacing: 1, textTransform: 'uppercase',
                                    cursor: h.key !== 'upd' ? 'pointer' : 'default', width: h.w || 'auto',
                                }}>
                                    {h.label} {sortBy === h.key ? (sortDir > 0 ? '↑' : '↓') : ''}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map(s => (
                            <tr key={s.id} style={{ borderBottom: '1px solid #1f1f1f', cursor: 'pointer', transition: 'background .1s' }}
                                onClick={() => onSelectShipment?.(s)}
                                onMouseEnter={e => e.currentTarget.style.background = '#262626'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                <td style={{ padding: '4px 6px', fontWeight: 700, color: '#e0e0e0' }}>{s.id}</td>
                                <td style={{ padding: '4px 6px', color: '#bbb' }}>{s.origin}</td>
                                <td style={{ padding: '4px 6px', color: '#bbb' }}>{s.destination}</td>
                                <td style={{ padding: '4px 6px', color: '#888' }}>{s.carrier}</td>
                                <td style={{ padding: '4px 6px', fontWeight: 700, color: sc(s.status) }}>{s.status}</td>
                                <td style={{ padding: '4px 6px', color: '#bbb' }}>{s.eta_hours}h</td>
                                <td style={{ padding: '4px 6px', color: s.current_cost > s.base_cost ? '#ef4444' : '#bbb' }}>₹{(s.current_cost || s.base_cost || 0).toLocaleString()}</td>
                                <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                                    {s.has_update && <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 6px #22c55e55' }}></span>}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
