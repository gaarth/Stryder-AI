import { useState, useMemo } from 'react';

export default function CRMTable({ shipments, onSelectShipment, filters, onFiltersChange }) {
    const [sortBy, setSortBy] = useState('id');
    const [sortDir, setSortDir] = useState(1);
    const [openDropdown, setOpenDropdown] = useState(null);

    // Extract unique values for each filter field
    const uniqueStatuses = useMemo(() => [...new Set(shipments.map(s => s.status))].sort(), [shipments]);
    const uniqueCarriers = useMemo(() => [...new Set(shipments.map(s => s.carrier))].sort(), [shipments]);
    const uniqueOrigins = useMemo(() => [...new Set(shipments.map(s => s.origin))].sort(), [shipments]);
    const uniqueDestinations = useMemo(() => [...new Set(shipments.map(s => s.destination))].sort(), [shipments]);

    // Apply filters
    const filtered = useMemo(() => {
        return shipments.filter(s => {
            if (filters.status.length && !filters.status.includes(s.status)) return false;
            if (filters.carrier.length && !filters.carrier.includes(s.carrier)) return false;
            if (filters.origin.length && !filters.origin.includes(s.origin)) return false;
            if (filters.destination.length && !filters.destination.includes(s.destination)) return false;
            return true;
        });
    }, [shipments, filters]);

    const sorted = useMemo(() => {
        return [...filtered].sort((a, b) => {
            if (sortBy === 'id') return (a.id - b.id) * sortDir;
            if (sortBy === 'status') return a.status.localeCompare(b.status) * sortDir;
            if (sortBy === 'origin') return a.origin.localeCompare(b.origin) * sortDir;
            if (sortBy === 'dest') return a.destination.localeCompare(b.destination) * sortDir;
            if (sortBy === 'carrier') return a.carrier.localeCompare(b.carrier) * sortDir;
            if (sortBy === 'eta') return (a.eta_hours - b.eta_hours) * sortDir;
            if (sortBy === 'cost') return ((a.current_cost || 0) - (b.current_cost || 0)) * sortDir;
            return 0;
        });
    }, [filtered, sortBy, sortDir]);

    const toggleSort = (col) => {
        if (sortBy === col) setSortDir(d => d * -1);
        else { setSortBy(col); setSortDir(1); }
    };

    const toggleFilter = (key, value) => {
        const current = filters[key];
        const updated = current.includes(value)
            ? current.filter(v => v !== value)
            : [...current, value];
        onFiltersChange({ ...filters, [key]: updated });
    };

    const clearAllFilters = () => {
        onFiltersChange({ status: [], carrier: [], origin: [], destination: [] });
    };

    const hasActiveFilters = filters.status.length || filters.carrier.length || filters.origin.length || filters.destination.length;

    const sc = (s) => s === 'DELAYED' ? 'var(--text-dim)' : s === 'AT_RISK' ? 'var(--text-muted)' : s === 'DELIVERED' ? 'var(--accent)' : 'var(--text-muted)';

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

    const FILTER_CONFIGS = [
        { key: 'status', label: 'Status', options: uniqueStatuses },
        { key: 'carrier', label: 'Carrier', options: uniqueCarriers },
        { key: 'origin', label: 'Origin', options: uniqueOrigins },
        { key: 'destination', label: 'Dest', options: uniqueDestinations },
    ];

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--glass-bg)', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{
                padding: '6px 14px', borderBottom: '1px solid var(--glass-border)', flexShrink: 0,
                fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, color: 'var(--text-muted)',
                letterSpacing: 1, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 8,
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-muted)' }}></span>
                CRM
                <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 9 }}>
                    {filtered.length}{filtered.length !== shipments.length ? ` / ${shipments.length}` : ''}
                </span>
            </div>

            {/* Filter Bar */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
                borderBottom: '1px solid var(--glass-border)', flexShrink: 0, flexWrap: 'wrap',
                background: 'rgba(255,255,255,0.02)',
            }}>
                {FILTER_CONFIGS.map(fc => {
                    const isOpen = openDropdown === fc.key;
                    const activeCount = filters[fc.key].length;
                    return (
                        <div key={fc.key} style={{ position: 'relative' }}>
                            <button
                                onClick={(e) => { e.stopPropagation(); setOpenDropdown(isOpen ? null : fc.key); }}
                                style={{
                                    fontFamily: 'var(--font-body)', fontSize: 11, fontWeight: 600,
                                    padding: '3px 8px', border: '1px solid', cursor: 'pointer',
                                    borderRadius: 'var(--radius-pill)', letterSpacing: 0.5,
                                    transition: 'all .2s var(--ease-smooth)',
                                    background: activeCount ? 'rgba(0,255,135,0.08)' : 'transparent',
                                    borderColor: activeCount ? 'var(--glass-border-hover)' : 'var(--glass-border)',
                                    color: activeCount ? 'var(--accent)' : 'var(--text-muted)',
                                }}
                            >
                                {fc.label}{activeCount ? ` (${activeCount})` : ''} ▾
                            </button>

                            {isOpen && (
                                <div
                                    onClick={e => e.stopPropagation()}
                                    style={{
                                        position: 'absolute', top: '100%', left: 0, marginTop: 4, zIndex: 200,
                                        background: 'rgba(10,10,10,0.95)', backdropFilter: 'blur(20px)',
                                        border: '1px solid var(--glass-border)', borderRadius: 'var(--radius)',
                                        minWidth: 160, maxHeight: 200, overflowY: 'auto',
                                        boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                                    }}
                                >
                                    {fc.options.map(opt => {
                                        const isSelected = filters[fc.key].includes(opt);
                                        return (
                                            <button
                                                key={opt}
                                                onClick={() => toggleFilter(fc.key, opt)}
                                                style={{
                                                    display: 'flex', alignItems: 'center', gap: 8,
                                                    width: '100%', padding: '6px 12px',
                                                    background: isSelected ? 'rgba(0,255,135,0.08)' : 'transparent',
                                                    border: 'none', color: isSelected ? 'var(--accent)' : 'var(--text)',
                                                    fontFamily: 'var(--font-body)', fontSize: 11,
                                                    cursor: 'pointer', textAlign: 'left',
                                                    transition: 'background .1s',
                                                }}
                                                onMouseEnter={e => !isSelected && (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                                                onMouseLeave={e => !isSelected && (e.currentTarget.style.background = 'transparent')}
                                            >
                                                <span style={{
                                                    width: 14, height: 14, borderRadius: 3, flexShrink: 0,
                                                    border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--glass-border)'}`,
                                                    background: isSelected ? 'var(--accent)' : 'transparent',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontSize: 9, color: '#000', fontWeight: 700,
                                                }}>
                                                    {isSelected ? '✓' : ''}
                                                </span>
                                                {opt}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    );
                })}

                {hasActiveFilters && (
                    <button
                        onClick={clearAllFilters}
                        style={{
                            fontFamily: 'var(--font-body)', fontSize: 11, fontWeight: 600,
                            padding: '3px 8px', border: '1px solid rgba(150,150,150,0.3)',
                            borderRadius: 'var(--radius-pill)', cursor: 'pointer',
                            background: 'rgba(150,150,150,0.08)', color: 'var(--text-muted)',
                            letterSpacing: 0.5, marginLeft: 'auto',
                            transition: 'all .2s var(--ease-smooth)',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(150,150,150,0.15)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'rgba(150,150,150,0.08)'}
                    >
                        Clear
                    </button>
                )}
            </div>

            {/* Table */}
            <div style={{ flex: 1, overflowY: 'auto' }} onClick={() => setOpenDropdown(null)}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-body)', fontSize: 12 }}>
                    <thead>
                        <tr style={{ position: 'sticky', top: 0, background: 'rgba(20,20,20,0.95)', backdropFilter: 'blur(8px)', zIndex: 1 }}>
                            {COLS.map(h => (
                                <th key={h.key} onClick={() => h.key !== 'upd' && toggleSort(h.key)} style={{
                                    padding: '6px 6px', textAlign: 'left', borderBottom: '1px solid var(--glass-border)',
                                    fontFamily: 'var(--font-display)', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: 1, textTransform: 'uppercase',
                                    cursor: h.key !== 'upd' ? 'pointer' : 'default', width: h.w || 'auto',
                                }}>
                                    {h.label} {sortBy === h.key ? (sortDir > 0 ? '↑' : '↓') : ''}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.map(s => (
                            <tr key={s.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', cursor: 'pointer', transition: 'background .15s' }}
                                onClick={() => onSelectShipment?.(s)}
                                onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,135,0.04)'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                <td style={{ padding: '4px 6px', fontWeight: 700, color: 'var(--text-primary)' }}>{s.id}</td>
                                <td style={{ padding: '4px 6px', color: 'var(--text-secondary)' }}>{s.origin}</td>
                                <td style={{ padding: '4px 6px', color: 'var(--text-secondary)' }}>{s.destination}</td>
                                <td style={{ padding: '4px 6px', color: 'var(--text-muted)' }}>{s.carrier}</td>
                                <td style={{ padding: '4px 6px', fontWeight: 700, color: sc(s.status) }}>{s.status}</td>
                                <td style={{ padding: '6px 6px', color: 'var(--text-secondary)' }}>{s.eta_hours}h</td>
                                <td style={{ padding: '6px 6px', color: s.current_cost > s.base_cost ? 'var(--text)' : 'var(--text-secondary)' }}>₹{(s.current_cost || s.base_cost || 0).toLocaleString()}</td>
                                <td style={{ padding: '6px 6px', textAlign: 'center' }}>
                                    {s.has_update && <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 6px rgba(0,255,135,0.35)' }}></span>}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
