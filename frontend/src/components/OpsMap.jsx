import { useEffect, useRef } from 'react';

export default function OpsMap({ shipments, ports, warehouses, onSelectShipment, onPortClick, onWhClick }) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const layersRef = useRef({ ships: [], ports: [], wh: [] });

    // Init map once
    useEffect(() => {
        let mounted = true;
        (async () => {
            const L = await import('leaflet');
            await import('leaflet/dist/leaflet.css');
            if (!mounted || !containerRef.current || mapRef.current) return;
            const map = L.map(containerRef.current, { center: [22, 79], zoom: 5, attributionControl: false, zoomControl: true });
            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { maxZoom: 18, subdomains: 'abcd' }).addTo(map);
            mapRef.current = map;
        })();
        return () => { mounted = false; if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
    }, []);

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
                    html: `<div style="width:18px;height:18px;background:${congColor};border:2px solid ${congColor}88;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:10px;color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.4);cursor:pointer;">⚓</div>`,
                    iconSize: [18, 18], iconAnchor: [9, 9],
                });
                const m = L.marker([p.lat, p.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:'JetBrains Mono',monospace;font-size:11px;min-width:140px;"><b>${p.name}</b><br/>Congestion: <span style="color:${congColor};font-weight:700">${p.congestion_level}</span> (${p.congestion_pct}%)<br/>Incoming: ${p.incoming_count}<br/>Throughput: ${p.throughput} TEU/day</div>`, { className: 'map-tip', direction: 'top', offset: [0, -10] });
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
                const utilColor = w.utilization_pct > 80 ? '#ef4444' : w.utilization_pct > 60 ? '#f59e0b' : '#1f2937';
                const icon = L.divIcon({
                    className: '',
                    html: `<div style="width:14px;height:14px;background:${utilColor};border:2px solid ${utilColor}88;border-radius:2px;box-shadow:0 1px 3px rgba(0,0,0,.3);cursor:pointer;"></div>`,
                    iconSize: [14, 14], iconAnchor: [7, 7],
                });
                const m = L.marker([w.lat, w.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:'JetBrains Mono',monospace;font-size:11px;min-width:130px;"><b>${w.name}</b><br/>Utilization: ${w.utilization_pct}%<br/>Capacity: ${w.capacity}<br/>Incoming: ${w.incoming_count}</div>`, { className: 'map-tip', direction: 'top', offset: [0, -8] });
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
                const border = isDelayed ? '#b91c1c' : isDelivered ? '#15803d' : '#1d4ed8';
                const sz = isDelayed ? 12 : 10;
                const icon = L.divIcon({
                    className: '',
                    html: `<div style="width:${sz}px;height:${sz}px;background:${bg};border:2px solid ${border};border-radius:50%;box-shadow:0 0 ${isDelayed ? '6' : '3'}px ${bg}66;cursor:pointer;"></div>`,
                    iconSize: [sz, sz], iconAnchor: [sz / 2, sz / 2],
                });
                const m = L.marker([s.lat, s.lon], { icon }).addTo(map);
                m.bindTooltip(`<div style="font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.6;min-width:160px;"><b>#${s.id}</b> ${s.origin}→${s.destination}<br/>Status: <span style="color:${bg};font-weight:700">${s.status}</span><br/>Carrier: ${s.carrier} | ETA: ${s.eta_hours}h<br/>Cost: ₹${s.current_cost?.toLocaleString() || s.base_cost?.toLocaleString()}${s.has_update ? '<br/><span style="color:#22c55e;font-weight:700">⟳ Fix Applied</span>' : ''}</div>`, { className: 'map-tip', direction: 'top', offset: [0, -8] });
                m.on('click', () => onSelectShipment?.(s));
                layersRef.current.ships.push(m);
            });
        });
    }, [shipments, onSelectShipment]);

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
            <style>{`
        .map-tip { background:#1a1a1a !important; color:#e0e0e0 !important; border:1px solid #333 !important; border-radius:6px !important; padding:8px 12px !important; box-shadow:0 4px 16px rgba(0,0,0,.5) !important; }
        .map-tip::before { border-top-color:#1a1a1a !important; }
      `}</style>
        </div>
    );
}
