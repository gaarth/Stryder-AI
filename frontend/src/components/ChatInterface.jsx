import { useState, useRef, useEffect, useCallback } from 'react';
import api from '../services/api';
import './ChatInterface.css';

const AGENTS = ['Sentinel', 'Strategist', 'Actuary', 'Executor', 'Cascade'];
const SUBTAGS = ['ETA_AGENT', 'DELAY_AGENT', 'CARRIER_AGENT', 'HUB_AGENT', 'CASCADE_MODEL'];
const AGENT_COLORS = {
    Sentinel: '#ef4444', Strategist: '#8b5cf6', Actuary: '#f59e0b',
    Executor: '#10b981', Cascade: '#06b6d4', System: '#00ff41',
};

const THINKING_MESSAGES = [
    '[SENTINEL] Scanning telemetry for Vishakhapatnam Port...',
    '[STRATEGIST] Consulting @CASCADE_MODEL for risk assessment...',
    '[ACTUARY] Calculating SLA breach vs. Reroute cost...',
    '[EXECUTOR] Formulating autonomous intervention...',
];

function ThinkingAnimation() {
    const [idx, setIdx] = useState(0);
    useEffect(() => {
        const timer = setInterval(() => setIdx(i => (i + 1) % THINKING_MESSAGES.length), 1200);
        return () => clearInterval(timer);
    }, []);
    return (
        <div className="thinking-anim">
            <span className="thinking-text">{THINKING_MESSAGES[idx]}</span>
        </div>
    );
}

function TypewriterText({ text, speed = 12, onDone }) {
    const [displayed, setDisplayed] = useState('');
    const idx = useRef(0);
    useEffect(() => {
        idx.current = 0;
        setDisplayed('');
        const timer = setInterval(() => {
            idx.current++;
            setDisplayed(text.slice(0, idx.current));
            if (idx.current >= text.length) {
                clearInterval(timer);
                onDone?.();
            }
        }, speed);
        return () => clearInterval(timer);
    }, [text, speed]);
    return <span>{displayed}<span className="type-cursor">|</span></span>;
}

export default function ChatInterface({ shipmentContext }) {
    const [messages, setMessages] = useState([
        { role: 'system', text: 'STRYDER AI Terminal ready. Tag agents: @Sentinel @Strategist @Actuary @Executor @Cascade', ts: new Date().toISOString() },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [suggestions, setSuggestions] = useState([]);
    const [typingId, setTypingId] = useState(null);
    const endRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, typingId]);

    // If shipment context provided, pre-fill
    useEffect(() => {
        if (shipmentContext) {
            setInput(`@Strategist analyze shipment ${shipmentContext}`);
            inputRef.current?.focus();
        }
    }, [shipmentContext]);

    const handleInput = (e) => {
        const val = e.target.value;
        setInput(val);
        const lastWord = val.split(' ').pop();
        if (lastWord.startsWith('@')) {
            const q = lastWord.slice(1).toLowerCase();
            if (lastWord.includes(':')) {
                const sub = lastWord.split(':')[1].toLowerCase();
                setSuggestions(SUBTAGS.filter(s => s.toLowerCase().startsWith(sub)).map(s => `@Strategist:${s}`));
            } else {
                setSuggestions(AGENTS.filter(a => a.toLowerCase().startsWith(q)).map(a => `@${a}`));
            }
        } else setSuggestions([]);
    };

    const applySuggestion = (s) => {
        const words = input.split(' ');
        words[words.length - 1] = s;
        setInput(words.join(' ') + ' ');
        setSuggestions([]);
        inputRef.current?.focus();
    };

    const send = async () => {
        if (!input.trim() || loading) return;
        const msg = input.trim();
        setInput(''); setSuggestions([]);
        const userMsg = { role: 'user', text: msg, ts: new Date().toISOString() };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);
        try {
            const result = await api.chat(msg);
            const id = Date.now();
            setMessages(prev => [...prev, {
                id, role: 'agent', agent: result.agent, subtag: result.subtag,
                text: result.response, ts: result.timestamp, typing: true,
            }]);
            setTypingId(id);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'error', text: `Error: ${err.message}`, ts: new Date().toISOString() }]);
        } finally { setLoading(false); }
    };

    const onTypeDone = useCallback((id) => {
        setTypingId(null);
        setMessages(prev => prev.map(m => m.id === id ? { ...m, typing: false } : m));
    }, []);

    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
        if (e.key === 'Tab' && suggestions.length) { e.preventDefault(); applySuggestion(suggestions[0]); }
    };

    // Add reasoning chain messages
    const addReasoningChain = useCallback((steps) => {
        let delay = 0;
        steps.forEach((step, i) => {
            setTimeout(() => {
                const id = Date.now() + i;
                setMessages(prev => [...prev, {
                    id, role: 'agent', agent: step.agent,
                    text: step.message, ts: new Date().toISOString(), typing: true,
                }]);
                setTypingId(id);
            }, delay);
            delay += 1500 + (step.message.length * 10);
        });
    }, []);

    // Expose addReasoningChain to parent
    useEffect(() => {
        window.__stryderChat = { addReasoningChain };
    }, [addReasoningChain]);

    return (
        <div className="panel chat-panel">
            <div className="panel-header">
                <span style={{ display: 'flex', alignItems: 'center' }}><span className="dot"></span>Agent Command Interface</span>
                {loading && <span className="chat-status">PROCESSING</span>}
            </div>
            <div className="chat-messages">
                {messages.map((m, i) => {
                    const color = AGENT_COLORS[m.agent] || 'var(--accent)';
                    return (
                        <div key={m.id || i} className={`chat-msg ${m.role}`}>
                            <div className="msg-tag" style={{ color: m.role === 'agent' ? color : undefined }}>
                                {m.role === 'agent' ? `[${m.agent}${m.subtag ? `:${m.subtag}` : ''}]` :
                                    m.role === 'user' ? '[YOU]' :
                                        m.role === 'system' ? '[SYS]' : '[ERR]'}
                            </div>
                            <div className="msg-body">
                                {m.typing && m.id === typingId ? (
                                    <TypewriterText text={m.text} speed={10} onDone={() => onTypeDone(m.id)} />
                                ) : (
                                    <span className="msg-text">{m.text}</span>
                                )}
                            </div>
                        </div>
                    );
                })}
                {loading && (
                    <div className="chat-msg agent">
                        <div className="msg-tag" style={{ color: '#22d3ee' }}>[THINKING]</div>
                        <div className="msg-body"><ThinkingAnimation /></div>
                    </div>
                )}
                <div ref={endRef} />
            </div>
            {suggestions.length > 0 && (
                <div className="chat-suggestions">
                    {suggestions.map(s => <button key={s} className="suggestion" onClick={() => applySuggestion(s)}>{s}</button>)}
                </div>
            )}
            <div className="chat-input-row">
                <input ref={inputRef} className="chat-input" value={input}
                    onChange={handleInput} onKeyDown={handleKey}
                    placeholder="@Sentinel scan for anomalies..." />
                <button className="btn primary" onClick={send} disabled={loading}>SEND</button>
            </div>
        </div>
    );
}
