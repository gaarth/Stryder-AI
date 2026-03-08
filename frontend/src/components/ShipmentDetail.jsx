export default function ShipmentDetail({ shipment, onClose, onOptimize, onAskAgent, onDismissUpdate }) {
    const s = shipment;
    const sc = s.status === 'DELAYED' ? '#ef4444' : s.status === 'DELIVERED' ? '#22c55e' : '#3b82f6';
    const penalty = Math.max(0, (s.current_cost || 0) - (s.base_cost || 0));

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 480 }}>
                <div className="modal-header">
                    <span>Shipment #{s.id}</span>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body" style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '6px 12px', marginBottom: 16 }}>
                        <span style={{ color: '#888' }}>Route</span><span style={{ color: '#e0e0e0' }}>{s.origin} → {s.destination}</span>
                        <span style={{ color: '#888' }}>Carrier</span><span style={{ color: '#e0e0e0' }}>{s.carrier}</span>
                        <span style={{ color: '#888' }}>Cargo</span><span style={{ color: '#999' }}>{s.cargo}</span>
                        <span style={{ color: '#888' }}>Status</span><span style={{ color: sc, fontWeight: 700 }}>{s.status}</span>
                        <span style={{ color: '#888' }}>ETA</span><span style={{ color: '#e0e0e0' }}>{s.eta_hours}h</span>
                        <span style={{ color: '#888' }}>Risk</span><span style={{ color: s.risk === 'High' ? '#ef4444' : s.risk === 'Medium' ? '#f59e0b' : '#888' }}>{s.risk}</span>
                    </div>

                    {/* Cost breakdown */}
                    <div style={{ borderTop: '1px solid #2a2a2a', paddingTop: 12, marginBottom: 12 }}>
                        <div style={{ fontSize: 10, fontWeight: 700, color: '#888', letterSpacing: 1, textTransform: 'uppercase', marginBottom: 8 }}>Cost Analysis</div>
                        <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '4px 12px' }}>
                            <span style={{ color: '#888' }}>Base Cost</span><span style={{ color: '#e0e0e0' }}>₹{(s.base_cost || 0).toLocaleString()}</span>
                            <span style={{ color: '#888' }}>Current Cost</span><span style={{ color: penalty > 0 ? '#ef4444' : '#e0e0e0', fontWeight: 700 }}>₹{(s.current_cost || 0).toLocaleString()}</span>
                            {penalty > 0 && <>
                                <span style={{ color: '#888' }}>Penalty Accrued</span><span style={{ color: '#ef4444' }}>+₹{penalty.toLocaleString()}</span>
                            </>}
                            <span style={{ color: '#888' }}>Penalty Rate</span><span style={{ color: '#999' }}>₹{(s.delay_penalty_per_hour || 0).toLocaleString()}/hour</span>
                        </div>
                    </div>

                    {/* Fix History */}
                    {s.fix_history?.length > 0 && (
                        <div style={{ borderTop: '1px solid #2a2a2a', paddingTop: 12, marginBottom: 12 }}>
                            <div style={{ fontSize: 10, fontWeight: 700, color: '#22c55e', letterSpacing: 1, marginBottom: 8, textTransform: 'uppercase' }}>
                                ⟳ Stryder Fixes ({s.fix_history.length})
                            </div>
                            {s.fix_history.map((f, i) => (
                                <div key={i} style={{ padding: '8px 10px', background: '#161616', borderRadius: 4, marginBottom: 6, border: '1px solid #222', fontSize: 11, lineHeight: 1.6 }}>
                                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{f.fix}</div>
                                    <div style={{ color: '#888' }}>
                                        Carrier: {f.old_carrier} → <span style={{ color: '#22c55e' }}>{f.new_carrier}</span>
                                    </div>
                                    <div style={{ color: '#888' }}>
                                        ETA: <span style={{ textDecoration: 'line-through', color: '#ef4444' }}>{f.old_eta}h</span> → <span style={{ color: '#22c55e' }}>{f.new_eta}h</span>
                                        {f.old_cost != null && <> | Cost: ₹{f.old_cost?.toLocaleString()} → ₹{f.new_cost?.toLocaleString()}</>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                        {s.status !== 'DELIVERED' && (
                            <button onClick={() => onOptimize?.(s.id)} style={{
                                flex: 1, padding: '10px', fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
                                background: '#1a1a1a', border: '1px solid #22c55e44', borderRadius: 6, color: '#22c55e', cursor: 'pointer',
                            }}>
                                ⚡ Optimize ETA
                            </button>
                        )}
                        <button onClick={() => onAskAgent?.(s.id)} style={{
                            flex: 1, padding: '10px', fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
                            background: '#1a1a1a', border: '1px solid #8b5cf644', borderRadius: 6, color: '#8b5cf6', cursor: 'pointer',
                        }}>
                            @Strategist Analyze
                        </button>
                    </div>
                    {s.has_update && (
                        <button onClick={() => onDismissUpdate?.(s.id)} style={{
                            width: '100%', marginTop: 8, fontFamily: 'var(--font-mono)', fontSize: 10, padding: '6px',
                            background: 'transparent', border: '1px solid #333', borderRadius: 4, color: '#666', cursor: 'pointer',
                        }}>Dismiss Update</button>
                    )}
                </div>
            </div>
        </div>
    );
}
