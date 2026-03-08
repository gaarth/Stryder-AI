import React, { useState, useEffect, useRef } from 'react';
import { useRealtimeTable } from '../lib/realtime';
import './AgentsLearningHub.css';

const MOCK_LEARNINGS = [
    {
        title: 'Product Price Cache Stale',
        desc: 'Redis cache serving stale data. Prices show as $0.00.',
        strategy: 'Flush Redis Cache',
        occurrences: 2, last: '05:48 PM',
        thoughts: [
            "Detected anomaly in product pricing stream: 1400 occurrences of $0.00 checkouts.",
            "Cross-referencing database layer vs cache layer...",
            "Database prices show correct values ($49.99, $129.00).",
            "Cache layer (Redis node-04) returns stale empty records for key pattern 'products:*'.",
            "Checking replication lag on Redis cluster... Lag is 0.",
            "Eviction policy triggered incorrectly? Memory usage at 99%.",
            "Flushing specific cache keys to force database read on next request.",
            "Verifying fix... 10/10 test requests returned correct prices.",
            "Fix applied. Monitoring alert suppressed."
        ]
    },
    {
        title: 'Shipping API Degraded',
        desc: 'FedEx API returning 503. Shipping estimates unavailable.',
        strategy: 'Switch to UPS Fallback',
        occurrences: 5, last: '10:48 PM',
        thoughts: [
            "Error rates spiking on /shipping/estimate endpoints.",
            "Upstream provider (FedEx API) returning HTTP 503 Service Unavailable.",
            "Checking FedEx status page... Unplanned outage confirmed.",
            "Evaluating fallback carriers: UPS, USPS, DHL.",
            "UPS API is healthy (99.9% uptime in last hour).",
            "Dynamically adjusting routing rules to prioritize UPS for all pending orders.",
            "Re-calculating costs for 850 in-flight carts... Complete.",
            "Fall-back successful. Error rates returned to baseline <0.1%."
        ]
    },
    {
        title: 'Database Replication Lag',
        desc: 'Read replica 45s behind primary. Stale inventory counts.',
        strategy: 'Rebuild Replication Slot',
        occurrences: 3, last: '04:15 PM',
        thoughts: [
            "Inventory sync mismatch detected across regions.",
            "US-East-1 shows 5 items, EU-West-1 shows 12 items for SKU-992.",
            "Checking postgres replication lag: 45 seconds on replica-02.",
            "Network latency is normal. Disk IO is normal.",
            "Replication slot 'eu_sync_slot' appears corrupted or stuck.",
            "Dropping and recreating replication slot.",
            "Initiating catch-up sync... 400MB to transfer.",
            "Sync complete. Lag is now 0.02s.",
            "Data consistency verified across all regions."
        ]
    },
    {
        title: 'Health Check Flapping',
        desc: 'ALB health check toggling healthy/unhealthy every 20s.',
        strategy: 'Increase Health Check Interval',
        occurrences: 2, last: '01:30 AM',
        thoughts: [
            "Target group 'web-tg' flapping state rapidly.",
            "Instance CPU is at 45% (normal). Memory at 60% (normal).",
            "Application logs show occasional 2-second spikes during GC sweeps.",
            "Current ALB health check timeout is 1 second.",
            "GC sweeps are causing timeout failures, marking instances unhealthy.",
            "Increasing ALB health check timeout to 5 seconds.",
            "Increasing interval to 30 seconds to provide more buffer.",
            "Monitoring... Target group stable for 5 minutes.",
            "Flapping resolved."
        ]
    },
    {
        title: 'SSL Certificate Expiring',
        desc: 'TLS cert expires in 2 hours. Mixed content warnings appearing.',
        strategy: 'Renew & Deploy Certificate',
        occurrences: 2, last: '03:55 AM',
        thoughts: [
            "Certificate expiry alert triggered. 2 hours remaining on *.stryder.ai.",
            "Auto-renewal script failed 14 days ago due to Let's Encrypt rate limiting.",
            "Checking rate limit status... Cleared.",
            "Triggering certbot manual renewal via DNS challenge.",
            "DNS TXT record updated via Route53 provider.",
            "Awaiting propagation... Verified.",
            "Certificate renewed successfully.",
            "Uploading to AWS ACM and attaching to terminating ALBs.",
            "Verifying TLS handshake... Expiry updated to 90 days from now."
        ]
    },
    {
        title: 'Thumbnail Queue Slow',
        desc: 'Image processing lambdas cold-starting. Thumbnails delayed 10s.',
        strategy: 'Provision Lambda Functions',
        occurrences: 1, last: '10:25 AM',
        thoughts: [
            "User complaint metrics peaking: thumbnails not loading quickly.",
            "Checking SQS highly-backlogged queue 'img-process-queue': 4,500 messages.",
            "Lambda invocation metrics show heavy cold-start penalties overhead.",
            "Concurrent executions capped at 100?",
            "Checking AWS limits... Yes, account limit reached.",
            "Requesting auto-quota increase... Approved (new limit: 1000).",
            "Updating function provisioning concurrency to 250 to pre-warm instances.",
            "Queue drained in 45 seconds.",
            "Thumbnail generation latency restored to <800ms."
        ]
    }
];

function ClaudeThinkingBox({ thoughts, isExpanded }) {
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (!isExpanded) {
            setCurrentIndex(0);
            return;
        }

        const id = setInterval(() => {
            setCurrentIndex(prev => {
                if (prev >= thoughts.length - 1) {
                    clearInterval(id);
                    return prev;
                }
                return prev + 1;
            });
        }, 1800);

        return () => clearInterval(id);
    }, [isExpanded, thoughts.length]);

    return (
        <div className={`claude-thinking-container ${isExpanded ? 'expanded' : ''}`}>
            <div style={{
                color: '#888888',
                fontStyle: 'italic',
                fontSize: 13,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                fontFamily: 'var(--font-sans)',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                opacity: 0.8
            }}>
                <span style={{ fontSize: 10, flexShrink: 0 }}>◆</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{thoughts[currentIndex] || ""}</span>
            </div>
        </div>
    );
}

export default function AgentsLearningHub() {
    const [loaded, setLoaded] = useState(false);
    const [expandedId, setExpandedId] = useState(null);
    const { data: realtimeLogs } = useRealtimeTable('agent_learning_logs', { limit: 20 });

    useEffect(() => {
        // Trigger mounting animation
        const timer = setTimeout(() => setLoaded(true), 50);
        return () => clearTimeout(timer);
    }, []);

    // Combine realtime data with mock data or just use realtime if available
    const displayLogs = realtimeLogs && realtimeLogs.length > 0
        ? realtimeLogs.map(l => ({
            id: l.id,
            title: `${l.agent_name} Optimization`,
            desc: l.log_message,
            strategy: 'AI Fix Applied',
            occurrences: 1,
            last: l.sim_time || 'Just now',
            thoughts: [l.log_message]
        }))
        : MOCK_LEARNINGS;

    return (
        <div className={`learning-hub-dashboard ${loaded ? 'visible' : ''}`}>
            <div className="lh-logs-list">
                {displayLogs.map((log, i) => {
                    const isExpanded = expandedId === (log.id || i);

                    return (
                        <div
                            key={log.id || i}
                            className={`lh-dashboard-card animate-in ${isExpanded ? 'is-expanded' : ''}`}
                            style={{ animationDelay: `${i * 0.05}s` }}
                            onClick={() => setExpandedId(isExpanded ? null : (log.id || i))}
                        >
                            <div className="lh-card-header">
                                <div className="lh-brand">
                                    <span className="lh-brand-icon">//</span>
                                    <span className="lh-brand-text">STRYDER LEARNING</span>
                                </div>
                                <div className="lh-expand-indicator">
                                    {isExpanded ? 'COLLAPSE ^' : 'EXPAND DETAILS v'}
                                </div>
                            </div>

                            {/* Title - Syne with Gradient */}
                            <h3 className="lh-card-title">{log.title}</h3>

                            {/* Desc - Inter */}
                            <p className="lh-card-desc">{log.desc}</p>

                            <div className="lh-card-footer">
                                <div className="lh-strategy-container">
                                    <div className="lh-strategy-label">▪ FIX STRATEGIES APPLIED</div>
                                    <div className="lh-strategy-pill">{log.strategy}</div>
                                </div>

                                <div className="lh-card-meta">
                                    <span style={{ fontVariantNumeric: 'tabular-nums', fontFamily: 'var(--font-mono)' }}>Occurrences: {log.occurrences}</span>
                                    <span style={{ fontVariantNumeric: 'tabular-nums', fontFamily: 'var(--font-mono)' }}>Last: {log.last}</span>
                                </div>
                            </div>

                            <ClaudeThinkingBox thoughts={log.thoughts} isExpanded={isExpanded} />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
