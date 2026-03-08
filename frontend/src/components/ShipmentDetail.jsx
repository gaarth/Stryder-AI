import React from 'react';

export default function ShipmentDetail({ shipment, onClose, onOptimize, onAskAgent, onDismissUpdate }) {
    const s = shipment;
    const sc = s.status === 'DELAYED' ? 'var(--status-danger)' : s.status === 'DELIVERED' ? 'var(--status-ok)' : 'var(--blue)';
    const penalty = Math.max(0, (s.current_cost || 0) - (s.base_cost || 0));

    return (
        <div className="modal-overlay" onClick={onClose} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(8px)', zIndex: 1000 }}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{
                position: 'relative',
                maxWidth: 480,
                width: '100%',
                background: 'rgba(10, 15, 25, 0.7)',
                backdropFilter: 'blur(30px)',
                WebkitBackdropFilter: 'blur(30px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderTop: '1px solid rgba(255, 255, 255, 0.2)',
                borderLeft: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '16px',
                boxShadow: '0 30px 60px rgba(0, 0, 0, 0.6), inset 0 0 40px rgba(91, 250, 203, 0.05)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                <div className="modal-header" style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                    fontFamily: 'var(--font-display)',
                    fontSize: '18px',
                    fontWeight: 800,
                    color: '#fff',
                    letterSpacing: '1px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <span style={{
                        background: 'linear-gradient(180deg, var(--white) 0%, rgba(255,255,255,0.7) 100%)',
                        WebkitBackgroundClip: 'text',
                        backgroundClip: 'text',
                        color: 'transparent',
                    }}>Shipment #{s.id}</span>
                </div>
                <button className="modal-close" onClick={onClose} style={{
                    position: 'absolute',
                    top: 14,
                    right: 14,
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '18px',
                    cursor: 'pointer',
                    width: '32px',
                    height: '32px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '8px',
                    transition: 'all 0.2s'
                }}>✕</button>

                <div className="modal-body" style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: '13px',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px'
                }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', gap: '8px 12px' }}>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Route</span>
                        <span style={{ color: 'var(--text)', fontWeight: 500 }}>{s.origin} → {s.destination}</span>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Carrier</span>
                        <span style={{ color: 'var(--text)', fontWeight: 500 }}>{s.carrier}</span>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Cargo</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{s.cargo}</span>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Status</span>
                        <span style={{ color: sc, fontWeight: 700, letterSpacing: '0.5px' }}>{s.status}</span>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>ETA</span>
                        <span style={{ color: 'var(--text)', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>{s.eta_hours}h</span>
                        <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>Risk</span>
                        <span style={{ color: s.risk === 'High' ? 'var(--status-danger)' : s.risk === 'Medium' ? 'var(--status-warning)' : 'var(--text-muted)', fontWeight: 600 }}>{s.risk}</span>
                    </div>

                    {/* Cost breakdown */}
                    <div style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.05)',
                        borderRadius: '12px',
                        padding: '16px',
                    }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', marginBottom: 12 }}>Cost Analysis</div>
                        <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '8px 12px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Base Cost</span>
                            <span style={{ color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>₹{(s.base_cost || 0).toLocaleString()}</span>
                            <span style={{ color: 'var(--text-muted)' }}>Current Cost</span>
                            <span style={{ color: penalty > 0 ? 'var(--status-danger)' : 'var(--text)', fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>₹{(s.current_cost || 0).toLocaleString()}</span>
                            {penalty > 0 && <>
                                <span style={{ color: 'var(--text-muted)' }}>Penalty Accrued</span>
                                <span style={{ color: 'var(--status-danger)', fontVariantNumeric: 'tabular-nums' }}>+₹{penalty.toLocaleString()}</span>
                            </>}
                            <span style={{ color: 'var(--text-muted)' }}>Penalty Rate</span>
                            <span style={{ color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>₹{(s.delay_penalty_per_hour || 0).toLocaleString()}/hour</span>
                        </div>
                    </div>

                    {/* Fix History */}
                    {s.fix_history?.length > 0 && (
                        <div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--status-ok)', letterSpacing: '1px', marginBottom: 12, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span>⟳ Stryder Fixes ({s.fix_history.length})</span>
                            </div>
                            {s.fix_history.map((f, i) => (
                                <div key={i} style={{ padding: '12px', background: 'rgba(0, 255, 135, 0.05)', borderRadius: '12px', marginBottom: 8, border: '1px solid rgba(0, 255, 135, 0.1)', fontSize: 12, lineHeight: 1.6 }}>
                                    <div style={{ color: 'var(--text)', fontWeight: 600, marginBottom: 4 }}>{f.fix}</div>
                                    <div style={{ color: 'var(--text-secondary)' }}>
                                        Carrier: {f.old_carrier} → <span style={{ color: 'var(--status-ok)', fontWeight: 500 }}>{f.new_carrier}</span>
                                    </div>
                                    <div style={{ color: 'var(--text-secondary)' }}>
                                        ETA: <span style={{ textDecoration: 'line-through', color: 'var(--status-danger)' }}>{f.old_eta}h</span> → <span style={{ color: 'var(--status-ok)', fontWeight: 500 }}>{f.new_eta}h</span>
                                        {f.old_cost != null && <> | Cost: ₹{f.old_cost?.toLocaleString()} → ₹{f.new_cost?.toLocaleString()}</>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                        {s.status !== 'DELIVERED' && (
                            <button onClick={() => onOptimize?.(s.id)} style={{
                                flex: 1, padding: '12px', fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700,
                                background: 'rgba(0, 255, 135, 0.1)', border: '1px solid rgba(0, 255, 135, 0.3)', borderRadius: '8px', color: '#00ff87', cursor: 'pointer', transition: 'all 0.2s',
                                boxShadow: '0 4px 12px rgba(0, 255, 135, 0.1)'
                            }}>
                                ⚡ OPTIMIZE ETA
                            </button>
                        )}
                        <button onClick={() => onAskAgent?.(s.id)} style={{
                            flex: 1, padding: '12px', fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700,
                            background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: '8px', color: '#8b5cf6', cursor: 'pointer', transition: 'all 0.2s',
                            boxShadow: '0 4px 12px rgba(139, 92, 246, 0.1)'
                        }}>
                            @Strategist Analyze
                        </button>
                    </div>
                    {s.has_update && (
                        <button onClick={() => onDismissUpdate?.(s.id)} style={{
                            width: '100%', marginTop: 2, fontFamily: 'var(--font-sans)', fontSize: 12, padding: '8px', fontWeight: 500,
                            background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', color: 'var(--text-secondary)', cursor: 'pointer', transition: 'all 0.2s'
                        }}>Dismiss Update</button>
                    )}
                </div>
            </div>
        </div>
    );
}
