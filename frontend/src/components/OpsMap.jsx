import { useEffect, useRef, useState } from 'react';

export default function OpsMap({ simTime, shipments, ports, warehouses, onSelectShipment, onPortClick, onWhClick, theme = 'dark' }) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const layersRef = useRef({ ships: [], ports: [], wh: [], tileDark: null, tileLight: null });
    const [showLegend, setShowLegend] = useState(false);

    // Init map once
    useEffect(() => {
        let mounted = true;
        (async () => {
            const L = await import('leaflet');
            await import('leaflet/dist/leaflet.css');
            if (!mounted || !containerRef.current || mapRef.current) return;
            const map = L.map(containerRef.current, { center: [22.5, 82.5], zoom: 5, minZoom: 4, maxBounds: [[5, 65], [38, 100]], maxBoundsViscosity: 0.8, attributionControl: false, zoomControl: true });

            // Render BOTH layers so they can transition opacity
            const lightLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { maxZoom: 18, subdomains: 'abcd', opacity: theme === 'light' ? 1 : 0 }).addTo(map);
            const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 18, subdomains: 'abcd', opacity: theme === 'dark' ? 1 : 0 }).addTo(map);

            // Add CSS transitions directly to the tile containers
            setTimeout(() => {
                if (lightLayer.getContainer()) lightLayer.getContainer().style.transition = 'opacity 0.6s ease';
                if (darkLayer.getContainer()) darkLayer.getContainer().style.transition = 'opacity 0.6s ease';
            }, 100);

            layersRef.current.tileLight = lightLayer;
            layersRef.current.tileDark = darkLayer;
            mapRef.current = map;
        })();
        return () => { mounted = false; if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
    }, []);

    // Handle theme toggle
    useEffect(() => {
        if (!layersRef.current.tileLight || !layersRef.current.tileDark) return;
        layersRef.current.tileLight.setOpacity(theme === 'light' ? 1 : 0);
        layersRef.current.tileDark.setOpacity(theme === 'dark' ? 1 : 0);
    }, [theme]);

    // Draw ports (clickable)
    useEffect(() => {
        const map = mapRef.current; if (!map || !ports.length) return;
        import('leaflet').then(L => {
            layersRef.current.ports.forEach(m => m.remove());
            layersRef.current.ports = [];
            ports.forEach(p => {
                const congColor = p.congestion_level === 'HIGH' ? '#ef4444' : p.congestion_level === 'MODERATE' ? '#f59e0b' : '#9ca3af';
                const icon = L.divIcon({
                    className: '',
                    html: `<div style="width:18px;height:18px;background:${congColor};border:2px solid ${congColor}88;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:bold;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.4);cursor:pointer;">P</div>`,
                    iconSize: [18, 18], iconAnchor: [9, 9],
                });
                const m = L.marker([p.lat, p.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:var(--font-body);font-size:11px;min-width:140px;"><b style="font-family:var(--font-display);font-size:12px">${p.name}</b><br/>Congestion: <span style="color:${congColor};font-weight:700">${p.congestion_level}</span> (${p.congestion_pct}%)<br/>Incoming: ${p.incoming_count}<br/>Throughput: ${p.throughput} TEU/day</div>`, { className: 'map-tip', direction: 'top', offset: [0, -10] });
                m.on('click', () => onPortClick?.(p));
                layersRef.current.ports.push(m);
            });
        });
    }, [ports, onPortClick]);

    // Draw warehouses (clickable)
    useEffect(() => {
        const map = mapRef.current; if (!map || !warehouses.length) return;
        import('leaflet').then(L => {
            layersRef.current.wh.forEach(m => m.remove());
            layersRef.current.wh = [];
            warehouses.forEach(w => {
                const utilColor = w.utilization_pct > 80 ? '#ef4444' : w.utilization_pct > 60 ? '#f59e0b' : '#6b7280';
                const icon = L.divIcon({
                    className: '',
                    html: `<div style="width:14px;height:14px;background:${utilColor};border:2px solid ${utilColor};border-radius:2px;box-shadow:0 0 8px ${utilColor}aa;cursor:pointer;"></div>`,
                    iconSize: [14, 14], iconAnchor: [7, 7],
                });
                const m = L.marker([w.lat, w.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:var(--font-body);font-size:11px;min-width:130px;"><b style="font-family:var(--font-display);font-size:12px">${w.name}</b><br/>Utilization: ${w.utilization_pct}%<br/>Capacity: ${w.capacity}<br/>Incoming: ${w.incoming_count}</div>`, { className: 'map-tip', direction: 'top', offset: [0, -8] });
                m.on('click', () => onWhClick?.(w));
                layersRef.current.wh.push(m);
            });
        });
    }, [warehouses, onWhClick]);

    // Draw shipments
    useEffect(() => {
        const map = mapRef.current; if (!map) return;
        import('leaflet').then(L => {
            layersRef.current.ships.forEach(m => m.remove());
            layersRef.current.ships = [];
            shipments.forEach(s => {
                const isDelayed = s.status === 'DELAYED' || s.disrupted;
                const isDelivered = s.status === 'DELIVERED';
                const bg = isDelayed ? '#ef4444' : isDelivered ? '#22c55e' : '#3b82f6';
                const border = isDelayed ? '#ff8a8a' : isDelivered ? '#86efac' : '#93c5fd';
                const sz = isDelayed ? 12 : 10;
                const icon = L.divIcon({
                    className: '',
                    html: `<div style="width:${sz}px;height:${sz}px;background:${bg};border:2px solid ${border};border-radius:50%;box-shadow:0 0 ${isDelayed ? '8' : '4'}px ${bg};cursor:pointer;"></div>`,
                    iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
                });
                const m = L.marker([s.lat, s.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:var(--font-body);font-size:11px;line-height:1.6;min-width:160px;"><b style="font-family:var(--font-display);font-size:12px">#${s.id}</b> ${s.origin}-${s.destination}<br/>Status: <span style="color:${bg};font-weight:700">${s.status}</span><br/>Carrier: ${s.carrier} | ETA: ${s.eta_hours}h<br/>Cost: $${s.current_cost?.toLocaleString() || s.base_cost?.toLocaleString()}${s.has_update ? '<br/><span style="color:#22c55e;font-weight:700">[Fix Applied]</span>' : ''}</div>`, { className: 'map-tip', direction: 'top', offset: [0, -8] });
                m.on('click', () => onSelectShipment?.(s));
                layersRef.current.ships.push(m);
            });
        });
    }, [shipments, onSelectShipment]);

    return (
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

            {/* Time Overlay */}
            <div style={{
                position: 'absolute', top: 12, left: 54, zIndex: 1000,
                background: 'rgba(10,10,10,0.8)', backdropFilter: 'blur(8px)',
                padding: '6px 14px', borderRadius: 'var(--radius)',
                color: 'var(--white)', fontFamily: 'var(--font-display)',
                fontSize: 16, fontWeight: 700, letterSpacing: 1,
                border: '1px solid var(--glass-border)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
                textShadow: '0 2px 4px rgba(0,0,0,0.8)'
            }}>
                {simTime}
            </div>

            {/* Legend Overlay */}
            <div style={{
                position: 'absolute', bottom: 20, left: 20, zIndex: 1000,
                background: 'rgba(20,20,20,0.85)', backdropFilter: 'blur(12px)',
                border: '1px solid var(--glass-border)', borderRadius: 'var(--radius)',
                color: 'var(--text)', fontFamily: 'var(--font-body)', fontSize: 11,
                boxShadow: '0 8px 32px rgba(0,0,0,0.5)', overflow: 'hidden',
                transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
                width: showLegend ? 200 : 80,
                maxHeight: showLegend ? '80vh' : 36,
            }}>
                <button
                    onClick={() => setShowLegend(!showLegend)}
                    style={{
                        width: '100%', padding: '8px 12px', background: 'transparent',
                        border: 'none', color: 'var(--accent)', fontWeight: 700,
                        fontFamily: 'var(--font-display)', fontSize: 11, cursor: 'pointer',
                        textAlign: 'left', display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', letterSpacing: 1, textTransform: 'uppercase'
                    }}
                >
                    LEGEND <span style={{ transition: 'transform 0.3s ease', transform: showLegend ? 'rotate(180deg)' : 'rotate(0deg)' }}>^</span>
                </button>

                <div className="custom-scroll" style={{
                    padding: '0 12px 12px 12px', display: 'flex', flexDirection: 'column', gap: 12,
                    opacity: showLegend ? 1 : 0, transition: 'opacity 0.3s ease', pointerEvents: showLegend ? 'auto' : 'none',
                    overflowY: 'auto', maxHeight: 'calc(80vh - 36px)',
                }}>
                    {/* Ports */}
                    <div>
                        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>PORTS</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 14, height: 14, background: '#ef4444', border: '1px solid #ef444488', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 'bold', color: '#fff' }}>P</div>
                                <span style={{ color: 'var(--text-muted)' }}>High Congestion</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 14, height: 14, background: '#f59e0b', border: '1px solid #f59e0b88', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 'bold', color: '#fff' }}>P</div>
                                <span style={{ color: 'var(--text-muted)' }}>Mod Congestion</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 14, height: 14, background: '#9ca3af', border: '1px solid #9ca3af88', borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 'bold', color: '#fff' }}>P</div>
                                <span style={{ color: 'var(--text-muted)' }}>Low Congestion</span>
                            </div>
                        </div>
                    </div>

                    {/* Warehouses */}
                    <div>
                        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>WAREHOUSES</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 12, height: 12, background: '#ef4444', border: '1px solid #ef444488', borderRadius: 2 }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>&gt;80% Utilized</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 12, height: 12, background: '#f59e0b', border: '1px solid #f59e0b', borderRadius: 2 }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>60-80% Utilized</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 12, height: 12, background: '#6b7280', border: '1px solid #6b7280', borderRadius: 2 }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>&lt;60% Utilized</span>
                            </div>
                        </div>
                    </div>

                    {/* Shipments */}
                    <div>
                        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6, fontSize: 10, letterSpacing: 1 }}>SHIPMENTS</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 10, height: 10, background: '#3b82f6', border: '2px solid #93c5fd', borderRadius: '50%', boxShadow: '0 0 4px #3b82f6' }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>In Transit</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 10, height: 10, background: '#ef4444', border: '2px solid #ff8a8a', borderRadius: '50%', boxShadow: '0 0 8px #ef4444' }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>Delayed / Risk</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <div style={{ width: 10, height: 10, background: '#22c55e', border: '2px solid #86efac', borderRadius: '50%', boxShadow: '0 0 4px #22c55e' }}></div>
                                <span style={{ color: 'var(--text-muted)' }}>Delivered</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
        .map-tip { background:#1a1a1a !important; color:#e0e0e0 !important; border:1px solid #333 !important; border-radius:6px !important; padding:8px 12px !important; box-shadow:0 4px 16px rgba(0,0,0,.5) !important; }
        .map-tip::before { border-top-color:#1a1a1a !important; }
      `}</style>
        </div>
    );
}
