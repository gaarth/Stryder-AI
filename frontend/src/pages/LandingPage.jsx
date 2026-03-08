import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * LandingPage — renders the static landing page inside the React app.
 * Loads the landing CSS and JS from public/ as external assets.
 */
export default function LandingPage() {
    const containerRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        // Load landing page CSS
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/landing-styles.css';
        link.id = 'landing-css';
        document.head.appendChild(link);

        // Load Lenis smooth scroll CSS
        const lenisCSS = document.createElement('link');
        lenisCSS.rel = 'stylesheet';
        lenisCSS.href = 'https://unpkg.com/lenis@1.1.18/dist/lenis.css';
        lenisCSS.id = 'lenis-css';
        document.head.appendChild(lenisCSS);

        // Load Google Fonts
        const fontsLink = document.createElement('link');
        fontsLink.rel = 'stylesheet';
        fontsLink.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Syne:wght@700;800&display=swap';
        fontsLink.id = 'landing-fonts';
        document.head.appendChild(fontsLink);

        // Load Lenis JS
        const lenisScript = document.createElement('script');
        lenisScript.src = 'https://unpkg.com/lenis@1.1.18/dist/lenis.min.js';
        lenisScript.id = 'lenis-js';
        document.head.appendChild(lenisScript);

        // Load landing page JS (after Lenis loads)
        lenisScript.onload = () => {
            const script = document.createElement('script');
            script.src = '/landing-script.js';
            script.id = 'landing-js';
            document.body.appendChild(script);
        };

        // Intercept clicks to "Enter Dashboard" / "Get Started"
        const handleClick = (e) => {
            const target = e.target.closest('a');
            if (!target) return;
            const href = target.getAttribute('href');
            if (href && (href.includes('localhost') || href === '#')) {
                e.preventDefault();
                if (href.includes('localhost') || target.textContent.includes('Dashboard') || target.textContent.includes('Get Started')) {
                    navigate('/terminal');
                }
            }
        };
        document.addEventListener('click', handleClick);

        return () => {
            // Cleanup on unmount
            document.getElementById('landing-css')?.remove();
            document.getElementById('lenis-css')?.remove();
            document.getElementById('landing-fonts')?.remove();
            document.getElementById('lenis-js')?.remove();
            document.getElementById('landing-js')?.remove();
            document.removeEventListener('click', handleClick);
        };
    }, [navigate]);

    return (
        <div ref={containerRef} dangerouslySetInnerHTML={{ __html: LANDING_HTML }} />
    );
}

// The landing page HTML (extracted from index.html, with localhost links replaced)
const LANDING_HTML = `
  <nav class="sticky-nav" id="stickyNav">
    <div class="sticky-nav__logo">STRYDER</div>
    <ul class="sticky-nav__links">
      <li><a href="#problems">Problems</a></li>
      <li><a href="#what-we-do">Solutions</a></li>
      <li><a href="#features">Features</a></li>
    </ul>
    <a href="/terminal" class="glass-btn glass-btn--nav">Enter Dashboard</a>
  </nav>

  <div class="media-layer">
    <div class="video-bg" aria-hidden="true">
      <video id="bgVideo1" class="bg-video active" muted playsinline preload="auto">
        <source src="/assets/video/bg.mp4" type="video/mp4" />
      </video>
      <video id="bgVideo2" class="bg-video" muted playsinline preload="auto">
        <source src="/assets/video/bg.mp4" type="video/mp4" />
      </video>
      <div class="video-overlay"></div>
    </div>

    <main class="hero" id="hero">
      <div class="hero__content">
        <p class="hero__label anim-fade-up" style="--delay: 0s">introducing</p>
        <h1 class="hero__title anim-fade-up" style="--delay: 0.2s">STRYDER</h1>
        <p class="hero__desc anim-fade-up" style="--delay: 0.4s">
          Stryder is the digital twin of the supply chain that doesn't just <span class="text-orange-gradient">monitor</span> it <span class="text-green-gradient">negotiates</span>.
        </p>
        <div class="hero__actions anim-fade-up" style="--delay: 0.6s">
          <a href="/terminal" class="glass-btn" id="ctaBtn">
            <span>Enter Dashboard</span>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </a>
          <a href="#features" class="glass-btn glass-btn--ghost" id="learnMoreBtn">Learn More</a>
        </div>
      </div>
    </main>
  </div>

  <div class="content-layer">
    <section class="problems" id="problems">
      <div class="problems__sticky">
        <h2 class="problems__heading">Is this you?</h2>
        <div class="problems__stream problems__stream--left">
          <span class="problem-tag">Late Pickup</span>
          <span class="problem-tag">Inventory Shortage</span>
          <span class="problem-tag">Carrier Delay</span>
          <span class="problem-tag">ETA Drift</span>
          <span class="problem-tag">Damaged Freight</span>
          <span class="problem-tag">Customs Hold</span>
        </div>
        <div class="problems__stream problems__stream--right">
          <span class="problem-tag">Warehouse Congestion</span>
          <span class="problem-tag">Route Disruption</span>
          <span class="problem-tag">Hub Bottleneck</span>
          <span class="problem-tag">Demand Spike</span>
          <span class="problem-tag">Capacity Crunch</span>
          <span class="problem-tag">Documentation Error</span>
        </div>
      </div>
    </section>

    <section class="we-got-you">
      <h2 class="we-got-you__heading reveal-slide-up">WE GOT YOU</h2>
    </section>

    <section class="what-we-do" id="what-we-do">
      <div class="what-we-do__overlay"></div>
      <div class="what-we-do__sticky-header">
        <h2 class="what-we-do__title reveal-slide-up">WHAT WE DO</h2>
      </div>
      <div class="container what-we-do__content">
        <div class="bento-grid">
          <div class="bento-card reveal-slide-up">
            <h3 class="bento-card__title">Predictive Routing</h3>
            <p class="bento-card__desc">Anticipate disruptions before they happen with intelligent node pathing.</p>
            <div style="margin-top: 2rem; display: flex; justify-content: center;">
              <a href="/terminal" class="glass-btn" style="width: 100%; justify-content: center;">Get Started</a>
            </div>
          </div>
          <div class="bento-card reveal-slide-up">
            <h3 class="bento-card__title">Dynamic Allocation</h3>
            <p class="bento-card__desc">Instantly reallocate resources and capacity to maintain flow and eliminate constraints.</p>
            <div style="margin-top: 2rem; display: flex; justify-content: center;">
              <a href="/terminal" class="glass-btn" style="width: 100%; justify-content: center;">Get Started</a>
            </div>
          </div>
          <div class="bento-card reveal-slide-up">
            <h3 class="bento-card__title">Global Visibility</h3>
            <p class="bento-card__desc">Achieve true end-to-end transparency across your entire supply chain network.</p>
            <div style="margin-top: 2rem; display: flex; justify-content: center;">
              <a href="/terminal" class="glass-btn" style="width: 100%; justify-content: center;">Get Started</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="features" id="features">
      <div class="container">
        <div class="features-header">
          <h2 class="split-text-header">
            <span class="split-word">Powerful</span>
            <span class="split-word">Features.</span>
          </h2>
        </div>

        <div class="feature-row">
          <div class="feature-row__content">
            <h3 class="feature-row__title reveal-slide-up">Predictive Routing</h3>
            <p class="feature-row__desc reveal-slide-up">Anticipate disruptions before they happen with continuous, AI-driven route optimization and network analysis.</p>
            <ul class="feature-list">
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Dynamic pathfinding across 10k+ nodes</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Real-time weather & traffic integration</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Automated carrier re-assignment</span></li>
            </ul>
          </div>
          <div class="feature-row__image reveal-from-right">
            <img src="/assets/predictive_routing.png" alt="Predictive Routing UI" />
            <div class="glow-backdrop"></div>
          </div>
        </div>

        <div class="feature-row feature-row--reverse">
          <div class="feature-row__content">
            <h3 class="feature-row__title reveal-slide-up">Dynamic Allocation</h3>
            <p class="feature-row__desc reveal-slide-up">Instantly reallocate resources and capacity to maintain flow and eliminate costly hub bottlenecks.</p>
            <ul class="feature-list">
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Automated load balancing</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Predictive overflow detection</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Smart spatial inventory management</span></li>
            </ul>
          </div>
          <div class="feature-row__image reveal-from-left">
            <img src="/assets/dynamic_allocation.png" alt="Dynamic Allocation UI" />
            <div class="glow-backdrop"></div>
          </div>
        </div>

        <div class="feature-row">
          <div class="feature-row__content">
            <h3 class="feature-row__title reveal-slide-up">Global Visibility</h3>
            <p class="feature-row__desc reveal-slide-up">Achieve true end-to-end transparency across your entire supply chain with real-time tracking and ETAs.</p>
            <ul class="feature-list">
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Live GPS & satellite tracking</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Autonomous anomaly detection</span></li>
              <li class="feature-list__item"><div class="feature-list__icon"><svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M3.5 8L6.5 11.5L13 4.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div><span>Supplier-to-customer SLA dashboards</span></li>
            </ul>
          </div>
          <div class="feature-row__image reveal-from-right">
            <img src="/assets/global_visibility.png" alt="Global Visibility UI" />
            <div class="glow-backdrop"></div>
          </div>
        </div>
      </div>
    </section>

    <section class="logo-cloud" id="partners">
      <div class="container">
        <h2 class="logo-cloud__title reveal-slide-up">
          <span class="text-muted">Trusted by experts.</span><br/>
          <span class="text-highlight">Used by the leaders.</span>
        </h2>
        <div class="logo-cloud__divider reveal-slide-up"></div>
        <div class="logo-cloud__slider-container reveal-slide-up">
          <div class="logo-cloud__slider">
            <img src="https://svgl.app/library/nvidia-wordmark-light.svg" alt="Nvidia" />
            <img src="https://svgl.app/library/supabase_wordmark_light.svg" alt="Supabase" />
            <img src="https://svgl.app/library/openai_wordmark_light.svg" alt="OpenAI" />
            <img src="https://svgl.app/library/turso-wordmark-light.svg" alt="Turso" />
            <img src="https://svgl.app/library/vercel_wordmark.svg" alt="Vercel" />
            <img src="https://svgl.app/library/github_wordmark_light.svg" alt="GitHub" />
            <img src="https://svgl.app/library/nvidia-wordmark-light.svg" alt="Nvidia" />
            <img src="https://svgl.app/library/supabase_wordmark_light.svg" alt="Supabase" />
            <img src="https://svgl.app/library/openai_wordmark_light.svg" alt="OpenAI" />
            <img src="https://svgl.app/library/turso-wordmark-light.svg" alt="Turso" />
            <img src="https://svgl.app/library/vercel_wordmark.svg" alt="Vercel" />
            <img src="https://svgl.app/library/github_wordmark_light.svg" alt="GitHub" />
          </div>
        </div>
        <div class="logo-cloud__divider reveal-slide-up" style="margin-bottom: var(--space-xl);"></div>
      </div>
    </section>

    <footer class="site-footer">
      <div class="container footer-container">
        <div class="footer-brand">
          <div class="footer-logo">STRYDER</div>
          <p>The next generation of intelligent, AI-powered movement and network architecture.</p>
        </div>
        <div class="footer-links-group">
          <div class="footer-column">
            <h4>Solutions</h4>
            <ul>
              <li><a href="#features">Predictive Routing</a></li>
              <li><a href="#features">Dynamic Allocation</a></li>
              <li><a href="#features">Global Visibility</a></li>
            </ul>
          </div>
          <div class="footer-column">
            <h4>Company</h4>
            <ul>
              <li><a href="#">About Us</a></li>
              <li><a href="#">Careers</a></li>
              <li><a href="#">Press</a></li>
            </ul>
          </div>
          <div class="footer-column">
            <h4>Contact & Legal</h4>
            <ul>
              <li><a href="#">Contact Us</a></li>
              <li><a href="#">Privacy Policy</a></li>
              <li><a href="#">Terms of Service</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; 2026 STRYDER Inc. All rights reserved.</p>
      </div>
    </footer>
  </div>
`;
