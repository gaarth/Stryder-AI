import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage() {
    const navigate = useNavigate();
    const v1Ref = useRef(null);
    const v2Ref = useRef(null);
    const stickyNavRef = useRef(null);
    const heroTitleRef = useRef(null);
    const problemsSectionRef = useRef(null);
    const leftStreamRef = useRef(null);
    const rightStreamRef = useRef(null);
    const whatWeDoRef = useRef(null);
    const whatWeDoOverlayRef = useRef(null);

    useEffect(() => {
        // ── Video Crossfade Loop ──
        const v1 = v1Ref.current;
        const v2 = v2Ref.current;

        if (v1 && v2) {
            const FADE_DURATION_CSS = 1.0;
            const PRE_FADE_OFFSET = 0.5;
            const BUFFER = FADE_DURATION_CSS + PRE_FADE_OFFSET;
            let activeVideo = v1;
            let inactiveVideo = v2;
            let isSwapping = false;

            v1.play().catch(() => { });

            function checkLoop() {
                if (activeVideo.duration && activeVideo.currentTime >= activeVideo.duration - BUFFER && !isSwapping) {
                    isSwapping = true;
                    inactiveVideo.currentTime = 0;
                    inactiveVideo.play().catch(() => { });
                    inactiveVideo.classList.add('active');
                    activeVideo.classList.remove('active');
                    setTimeout(() => {
                        activeVideo.pause();
                        const temp = activeVideo;
                        activeVideo = inactiveVideo;
                        inactiveVideo = temp;
                        isSwapping = false;
                    }, FADE_DURATION_CSS * 1000 + 50);
                }
                requestAnimationFrame(checkLoop);
            }

            v1.addEventListener('ended', () => v1.play());
            v2.addEventListener('ended', () => v2.play());
            requestAnimationFrame(checkLoop);
        }

        // ── Sticky Nav ──
        const stickyNav = stickyNavRef.current;
        const heroTitle = heroTitleRef.current;
        if (stickyNav && heroTitle) {
            const navObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const isAboveViewport = entry.boundingClientRect.bottom < 0;
                    if (!entry.isIntersecting && isAboveViewport) {
                        stickyNav.classList.add('is-visible');
                    } else {
                        stickyNav.classList.remove('is-visible');
                    }
                });
            }, { threshold: 0, rootMargin: '0px' });
            navObserver.observe(heroTitle);
            return () => navObserver.disconnect();
        }
    }, []);

    useEffect(() => {
        // ── Scrollytelling ──
        const problemsSection = problemsSectionRef.current;
        const leftTags = leftStreamRef.current?.querySelectorAll('.problem-tag') || [];
        const rightTags = rightStreamRef.current?.querySelectorAll('.problem-tag') || [];

        if (!problemsSection || leftTags.length === 0) return;

        let isProblemsVisible = false;
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => { isProblemsVisible = entry.isIntersecting; });
        }, { threshold: 0, rootMargin: '100px 0px 100px 0px' });
        observer.observe(problemsSection);

        const totalScrollRange = 2.0;
        const staggerOffset = 0.35;

        function animateTags(tags, progress, range, overlap, globalDelayOffset) {
            const viewportH = window.innerHeight;
            const startY = viewportH + 50;
            const endY = -200;
            const totalTravel = startY - endY;

            tags.forEach((tag, idx) => {
                const delay = (idx * overlap) + globalDelayOffset;
                let localProgress = (progress * range) - delay;
                localProgress = Math.max(0, Math.min(1, localProgress));
                const currentY = startY - (localProgress * totalTravel);

                let opacity = 0;
                if (localProgress > 0 && localProgress < 0.15) {
                    opacity = localProgress / 0.15;
                } else if (localProgress >= 0.15 && localProgress < 0.6) {
                    opacity = 1;
                } else if (localProgress >= 0.6 && localProgress <= 0.8) {
                    opacity = 1 - ((localProgress - 0.6) / 0.2);
                }

                const isRightSide = tags === rightTags;
                const driftX = Math.sin(localProgress * Math.PI) * (isRightSide ? -30 : 30);
                tag.style.transform = `translate3d(${driftX}px, ${currentY}px, 0)`;
                tag.style.opacity = opacity.toFixed(2);
            });
        }

        function updateScrollytelling() {
            if (!isProblemsVisible) { requestAnimationFrame(updateScrollytelling); return; }
            const rect = problemsSection.getBoundingClientRect();
            const windowHeight = window.innerHeight;
            const distanceScrolled = windowHeight - rect.top;
            const totalScrollableDistance = rect.height + windowHeight;
            const progress = Math.max(0, Math.min(1, distanceScrolled / totalScrollableDistance));
            animateTags(leftTags, progress, totalScrollRange, staggerOffset, 0);
            animateTags(rightTags, progress, totalScrollRange, staggerOffset, staggerOffset / 2);
            requestAnimationFrame(updateScrollytelling);
        }

        requestAnimationFrame(updateScrollytelling);

        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        // ── Reveal Animations ──
        const revealElements = document.querySelectorAll(
            '.landing-page .split-word, .landing-page .reveal-slide-up, .landing-page .feature-list__item, .landing-page .reveal-from-left, .landing-page .reveal-from-right'
        );

        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    let delay = 0;
                    if (target.classList.contains('split-word')) {
                        const siblings = Array.from(target.parentNode.children);
                        delay = siblings.indexOf(target) * 150;
                    } else if (target.classList.contains('feature-list__item')) {
                        const siblings = Array.from(target.parentNode.children);
                        delay = siblings.indexOf(target) * 150 + 200;
                    } else if (target.classList.contains('reveal-slide-up') && target.tagName !== 'H3') {
                        delay = 100;
                    }
                    if (delay > 0) target.style.transitionDelay = `${delay}ms`;
                    target.classList.add('is-revealed');
                    revealObserver.unobserve(target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });

        revealElements.forEach(el => revealObserver.observe(el));
        return () => revealObserver.disconnect();
    }, []);

    useEffect(() => {
        // ── What We Do Darkening Overlay ──
        const whatWeDoSection = whatWeDoRef.current;
        const overlay = whatWeDoOverlayRef.current;
        if (!whatWeDoSection || !overlay) return;

        function onScroll() {
            const rect = whatWeDoSection.getBoundingClientRect();
            const windowH = window.innerHeight;
            const fadeStart = 0;
            const fadeEnd = -windowH * 0.4;
            if (rect.top > fadeStart) {
                overlay.style.opacity = '0';
            } else if (rect.top <= fadeStart && rect.top >= fadeEnd) {
                let p = (rect.top - fadeStart) / (fadeEnd - fadeStart);
                overlay.style.opacity = (p * 0.85).toFixed(3);
            } else {
                overlay.style.opacity = '0.85';
            }
        }

        window.addEventListener('scroll', onScroll);
        return () => window.removeEventListener('scroll', onScroll);
    }, []);

    const goToDashboard = (e) => {
        e.preventDefault();
        navigate('/terminal');
    };

    const CheckIcon = () => (
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );

    const SmallCheckIcon = () => (
        <svg width="10" height="10" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );

    return (
        <div className="landing-page">
            {/* Sticky Nav */}
            <nav className="sticky-nav" ref={stickyNavRef}>
                <div className="sticky-nav__logo">STRYDER</div>
                <ul className="sticky-nav__links">
                    <li><a href="#problems">Problems</a></li>
                    <li><a href="#what-we-do">Solutions</a></li>
                    <li><a href="#features">Features</a></li>
                </ul>
                <a href="/terminal" onClick={goToDashboard} className="glass-btn glass-btn--nav">Enter Dashboard</a>
            </nav>

            {/* Media Layer: Video + Hero */}
            <div className="media-layer">
                <div className="video-bg" aria-hidden="true">
                    <video ref={v1Ref} className="bg-video active" muted playsInline preload="auto">
                        <source src="/assets/video/bg.mp4" type="video/mp4" />
                    </video>
                    <video ref={v2Ref} className="bg-video" muted playsInline preload="auto">
                        <source src="/assets/video/bg.mp4" type="video/mp4" />
                    </video>
                    <div className="video-overlay"></div>
                </div>

                <main className="hero" id="hero">
                    <div className="hero__content">
                        <p className="hero__label anim-fade-up" style={{ '--delay': '0s' }}>introducing</p>
                        <h1 className="hero__title anim-fade-up" style={{ '--delay': '0.2s' }} ref={heroTitleRef}>STRYDER</h1>
                        <p className="hero__desc anim-fade-up" style={{ '--delay': '0.4s' }}>
                            Stryder is the digital twin of the supply chain that doesn't just <span className="text-orange-gradient">monitor</span> it <span className="text-green-gradient">negotiates</span>.
                        </p>
                        <div className="hero__actions anim-fade-up" style={{ '--delay': '0.6s' }}>
                            <a href="/terminal" onClick={goToDashboard} className="glass-btn" id="ctaBtn">
                                <span>Enter Dashboard</span>
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </a>
                            <a href="#features" className="glass-btn glass-btn--ghost" id="learnMoreBtn">Learn More</a>
                        </div>
                    </div>
                </main>
            </div>

            {/* Content Layer */}
            <div className="content-layer">
                {/* Scrollytelling: Problems */}
                <section className="problems" id="problems" ref={problemsSectionRef}>
                    <div className="problems__sticky">
                        <h2 className="problems__heading">Is this you?</h2>
                        <div className="problems__stream problems__stream--left" ref={leftStreamRef}>
                            <span className="problem-tag">Late Pickup</span>
                            <span className="problem-tag">Inventory Shortage</span>
                            <span className="problem-tag">Carrier Delay</span>
                            <span className="problem-tag">ETA Drift</span>
                            <span className="problem-tag">Damaged Freight</span>
                            <span className="problem-tag">Customs Hold</span>
                        </div>
                        <div className="problems__stream problems__stream--right" ref={rightStreamRef}>
                            <span className="problem-tag">Warehouse Congestion</span>
                            <span className="problem-tag">Route Disruption</span>
                            <span className="problem-tag">Hub Bottleneck</span>
                            <span className="problem-tag">Demand Spike</span>
                            <span className="problem-tag">Capacity Crunch</span>
                            <span className="problem-tag">Documentation Error</span>
                        </div>
                    </div>
                </section>

                {/* We Got You */}
                <section className="we-got-you">
                    <h2 className="we-got-you__heading reveal-slide-up">WE GOT YOU</h2>
                </section>

                {/* What We Do Bento Grid */}
                <section className="what-we-do" id="what-we-do" ref={whatWeDoRef}>
                    <div className="what-we-do__overlay" ref={whatWeDoOverlayRef}></div>
                    <div className="what-we-do__sticky-header">
                        <h2 className="what-we-do__title reveal-slide-up">WHAT WE DO</h2>
                    </div>
                    <div className="container what-we-do__content">
                        <div className="lp-bento-grid">
                            {/* Bento Box 1 */}
                            <div className="lp-bento-card reveal-slide-up">
                                <h3 className="lp-bento-card__title">Predictive Routing</h3>
                                <p className="lp-bento-card__desc">Anticipate disruptions before they happen with intelligent node pathing.</p>
                                <ul className="feature-list" style={{ marginTop: '1rem' }}>
                                    {['Dynamic pathfinding across 10k+ nodes', 'Real-time weather & traffic integration', 'Automated carrier re-assignment'].map((t, i) => (
                                        <li key={i} className="feature-list__item" style={{ opacity: 1, transform: 'none', fontSize: '0.9rem' }}>
                                            <div className="feature-list__icon" style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                <SmallCheckIcon />
                                            </div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
                                    <a href="/terminal" onClick={goToDashboard} className="glass-btn" style={{ width: '100%', justifyContent: 'center' }}>Get Started</a>
                                </div>
                            </div>

                            {/* Bento Box 2 */}
                            <div className="lp-bento-card reveal-slide-up">
                                <h3 className="lp-bento-card__title">Dynamic Allocation</h3>
                                <p className="lp-bento-card__desc">Instantly reallocate resources and capacity to maintain flow and eliminate constraints.</p>
                                <ul className="feature-list" style={{ marginTop: '1rem' }}>
                                    {['Automated load balancing', 'Predictive overflow detection', 'Smart spatial inventory management'].map((t, i) => (
                                        <li key={i} className="feature-list__item" style={{ opacity: 1, transform: 'none', fontSize: '0.9rem' }}>
                                            <div className="feature-list__icon" style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                <SmallCheckIcon />
                                            </div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
                                    <a href="/terminal" onClick={goToDashboard} className="glass-btn" style={{ width: '100%', justifyContent: 'center' }}>Get Started</a>
                                </div>
                            </div>

                            {/* Bento Box 3 */}
                            <div className="lp-bento-card reveal-slide-up">
                                <h3 className="lp-bento-card__title">Global Visibility</h3>
                                <p className="lp-bento-card__desc">Achieve true end-to-end transparency across your entire supply chain network.</p>
                                <ul className="feature-list" style={{ marginTop: '1rem' }}>
                                    {['Live GPS & satellite tracking', 'Customs clearing ETAs', 'Vendor compliance dashboards'].map((t, i) => (
                                        <li key={i} className="feature-list__item" style={{ opacity: 1, transform: 'none', fontSize: '0.9rem' }}>
                                            <div className="feature-list__icon" style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                <SmallCheckIcon />
                                            </div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                                <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
                                    <a href="/terminal" onClick={goToDashboard} className="glass-btn" style={{ width: '100%', justifyContent: 'center' }}>Get Started</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Features Section */}
                <section className="features" id="features">
                    <div className="container">
                        <div className="features-header">
                            <h2 className="split-text-header">
                                <span className="split-word">Powerful</span>{' '}
                                <span className="split-word">Features.</span>
                            </h2>
                        </div>

                        {/* Row 1 */}
                        <div className="feature-row">
                            <div className="feature-row__content">
                                <h3 className="feature-row__title reveal-slide-up">Predictive Routing</h3>
                                <p className="feature-row__desc reveal-slide-up">
                                    Anticipate disruptions before they happen with continuous, AI-driven route optimization and network analysis.
                                </p>
                                <ul className="feature-list">
                                    {['Dynamic pathfinding across 10k+ nodes', 'Real-time weather & traffic integration', 'Automated carrier re-assignment'].map((t, i) => (
                                        <li key={i} className="feature-list__item">
                                            <div className="feature-list__icon"><CheckIcon /></div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="feature-row__image reveal-from-right">
                                <img src="/assets/predictive_routing.png" alt="Predictive Routing UI" />
                                <div className="glow-backdrop"></div>
                            </div>
                        </div>

                        {/* Row 2 */}
                        <div className="feature-row feature-row--reverse">
                            <div className="feature-row__content">
                                <h3 className="feature-row__title reveal-slide-up">Dynamic Allocation</h3>
                                <p className="feature-row__desc reveal-slide-up">
                                    Instantly reallocate resources and capacity to maintain flow and eliminate costly hub bottlenecks.
                                </p>
                                <ul className="feature-list">
                                    {['Automated load balancing', 'Predictive overflow detection', 'Smart spatial inventory management'].map((t, i) => (
                                        <li key={i} className="feature-list__item">
                                            <div className="feature-list__icon"><CheckIcon /></div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="feature-row__image reveal-from-left">
                                <img src="/assets/dynamic_allocation.png" alt="Dynamic Allocation UI" />
                                <div className="glow-backdrop"></div>
                            </div>
                        </div>

                        {/* Row 3 */}
                        <div className="feature-row">
                            <div className="feature-row__content">
                                <h3 className="feature-row__title reveal-slide-up">Global Visibility</h3>
                                <p className="feature-row__desc reveal-slide-up">
                                    Achieve true end-to-end transparency across your entire supply chain with real-time tracking and ETAs.
                                </p>
                                <ul className="feature-list">
                                    {['Live GPS & satellite tracking', 'Autonomous anomaly detection', 'Supplier-to-customer SLA dashboards'].map((t, i) => (
                                        <li key={i} className="feature-list__item">
                                            <div className="feature-list__icon"><CheckIcon /></div>
                                            <span>{t}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="feature-row__image reveal-from-right">
                                <img src="/assets/global_visibility.png" alt="Global Visibility UI" />
                                <div className="glow-backdrop"></div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Logo Cloud */}
                <section className="logo-cloud" id="partners">
                    <div className="container">
                        <h2 className="logo-cloud__title reveal-slide-up">
                            <span className="text-muted">Trusted by experts.</span><br />
                            <span className="text-highlight">Used by the leaders.</span>
                        </h2>
                        <div className="logo-cloud__divider reveal-slide-up"></div>
                        <div className="logo-cloud__slider-container reveal-slide-up">
                            <div className="logo-cloud__slider">
                                {[
                                    'nvidia-wordmark-light', 'supabase_wordmark_light', 'openai_wordmark_light',
                                    'turso-wordmark-light', 'vercel_wordmark', 'github_wordmark_light',
                                    'claude-ai-wordmark-icon_light', 'clerk-wordmark-light'
                                ].flatMap((n, i) => [
                                    <img key={`a${i}`} src={`https://svgl.app/library/${n}.svg`} alt={n} />,
                                    <img key={`b${i}`} src={`https://svgl.app/library/${n}.svg`} alt={n} />
                                ])}
                            </div>
                        </div>
                        <div className="logo-cloud__divider reveal-slide-up" style={{ marginBottom: 'var(--space-xl)' }}></div>
                    </div>
                </section>

                {/* Footer */}
                <footer className="site-footer">
                    <div className="container footer-container">
                        <div className="footer-brand">
                            <div className="footer-logo">STRYDER</div>
                            <p>The next generation of intelligent, AI-powered movement and network architecture.</p>
                        </div>
                        <div className="footer-links-group">
                            <div className="footer-column">
                                <h4>Solutions</h4>
                                <ul>
                                    <li><a href="#features">Predictive Routing</a></li>
                                    <li><a href="#features">Dynamic Allocation</a></li>
                                    <li><a href="#features">Global Visibility</a></li>
                                </ul>
                            </div>
                            <div className="footer-column">
                                <h4>Company</h4>
                                <ul>
                                    <li><a href="#">About Us</a></li>
                                    <li><a href="#">Careers</a></li>
                                    <li><a href="#">Press</a></li>
                                </ul>
                            </div>
                            <div className="footer-column">
                                <h4>Contact &amp; Legal</h4>
                                <ul>
                                    <li><a href="#">Contact Us</a></li>
                                    <li><a href="#">Privacy Policy</a></li>
                                    <li><a href="#">Terms of Service</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div className="footer-bottom">
                        <p>&copy; 2026 STRYDER Inc. All rights reserved.</p>
                    </div>
                </footer>
            </div>
        </div>
    );
}
