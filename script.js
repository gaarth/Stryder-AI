/* ═══════════════════════════════════════════════════════════════
   STRYDER — Script
   Advanced dual-video crossfade for a perfect seamless loop
   Scrollytelling animations
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ───────── Smooth Scrolling (Lenis) ───────── */
  const lenis = new Lenis({
    duration: 1.2,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    direction: 'vertical',
    gestureDirection: 'vertical',
    smooth: true,
    mouseMultiplier: 1,
    smoothTouch: false,
    touchMultiplier: 2,
    infinite: false,
  });

  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }

  requestAnimationFrame(raf);

  /* ───────── Video Loop ───────── */
  const v1 = document.getElementById('bgVideo1');
  const v2 = document.getElementById('bgVideo2');

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

    v1.addEventListener('ended', () => { v1.play() });
    v2.addEventListener('ended', () => { v2.play() });

    document.addEventListener('click', function startVideo() {
      activeVideo.play().catch(() => { });
      document.removeEventListener('click', startVideo);
    }, { once: true });

    requestAnimationFrame(checkLoop);
  }

  /* ───────── Sticky Nav Animation ───────── */
  const stickyNav = document.getElementById('stickyNav');
  const heroTitle = document.querySelector('.hero__title');

  if (stickyNav && heroTitle) {
    const navObserver = new IntersectionObserver((entries) => {
      // IntersectionObserver fires when element enters/exits viewport
      // If hero title is NOT intersecting (it scrolled out of view upwards), show the nav!
      entries.forEach(entry => {
        // We only care if the element is scrolling out of view towards the top of the screen
        const isAboveViewport = entry.boundingClientRect.bottom < 0;

        if (!entry.isIntersecting && isAboveViewport) {
          stickyNav.classList.add('is-visible');
        } else {
          stickyNav.classList.remove('is-visible');
        }
      });
    }, {
      threshold: 0,
      rootMargin: "0px"
    });

    navObserver.observe(heroTitle);
  }

  /* ───────── Scrollytelling ───────── */
  const problemsSection = document.getElementById('problems');
  const leftTags = document.querySelectorAll('.problems__stream--left .problem-tag');
  const rightTags = document.querySelectorAll('.problems__stream--right .problem-tag');

  if (!problemsSection || leftTags.length === 0) return;

  let isProblemsVisible = false;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      isProblemsVisible = entry.isIntersecting;
    });
  }, { threshold: 0, rootMargin: '100px 0px 100px 0px' });

  observer.observe(problemsSection);

  // Stagger configurations
  const totalScrollRange = 2.0; // Slower scroll mapping
  const staggerOffset = 0.35; // Huge delay between tags to ensure they don't clump

  function updateScrollytelling() {
    if (!isProblemsVisible) {
      requestAnimationFrame(updateScrollytelling);
      return;
    }

    const rect = problemsSection.getBoundingClientRect();
    const windowHeight = window.innerHeight;

    const distanceScrolled = windowHeight - rect.top;
    const totalScrollableDistance = rect.height + windowHeight;
    let rawProgress = distanceScrolled / totalScrollableDistance;

    // Clamp between 0 and 1
    const progress = Math.max(0, Math.min(1, rawProgress));

    // Right side timeline is shifted exactly half a stagger offset so they alternate
    animateTags(leftTags, progress, totalScrollRange, staggerOffset, 0);
    animateTags(rightTags, progress, totalScrollRange, staggerOffset, staggerOffset / 2);

    requestAnimationFrame(updateScrollytelling);
  }

  function animateTags(tags, progress, range, overlap, globalDelayOffset) {
    const viewportH = window.innerHeight;
    const startY = viewportH + 50;
    const endY = -200;
    const totalTravel = startY - endY;

    tags.forEach((tag, idx) => {
      // Offset start time for each tag heavily
      const delay = (idx * overlap) + globalDelayOffset;

      let localProgress = (progress * range) - delay;
      localProgress = Math.max(0, Math.min(1, localProgress));

      const currentY = startY - (localProgress * totalTravel);

      // Fast fade in and fast fade out to ensure they don't linger on screen
      let opacity = 0;
      if (localProgress > 0 && localProgress < 0.15) {
        opacity = localProgress / 0.15; // Fade in quicker
      } else if (localProgress >= 0.15 && localProgress < 0.6) {
        opacity = 1; // Visible portion is shorter to guarantee max 2 on screen
      } else if (localProgress >= 0.6 && localProgress <= 0.8) {
        opacity = 1 - ((localProgress - 0.6) / 0.2); // Fade out early
      }

      // Add a slight horizontal drift for a feeling of floating
      const isRightSide = tags === rightTags;
      const driftX = Math.sin(localProgress * Math.PI) * (isRightSide ? -30 : 30);

      // Apply GPU-accelerated transforms
      tag.style.transform = `translate3d(${driftX}px, ${currentY}px, 0)`;
      tag.style.opacity = opacity.toFixed(2);
    });
  }

  // Start animation loop
  requestAnimationFrame(updateScrollytelling);
  /* ───────── Dynamic Reveal Animations ───────── */
  const revealElements = document.querySelectorAll(
    '.split-word, .reveal-slide-up, .feature-list__item, .reveal-from-left, .reveal-from-right'
  );

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        // Find if this is part of a staggered group
        const target = entry.target;

        let delay = 0;
        if (target.classList.contains('split-word')) {
          const siblings = Array.from(target.parentNode.children);
          delay = siblings.indexOf(target) * 150; // stagger header by 150ms
        } else if (target.classList.contains('feature-list__item')) {
          const siblings = Array.from(target.parentNode.children);
          delay = siblings.indexOf(target) * 150 + 200; // stagger list by 150ms, slightly deferred after title
        } else if (target.classList.contains('reveal-slide-up') && target.tagName !== 'H3') {
          delay = 100; // paragraph slightly after H3
        }

        if (delay > 0) {
          target.style.transitionDelay = `${delay}ms`;
        }

        // Add class to reveal
        target.classList.add('is-revealed');

        // Stop observing once revealed so it plays once smoothly
        revealObserver.unobserve(target);
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px' // slightly trigger before entering fully
  });

  revealElements.forEach(el => revealObserver.observe(el));

  /* ───────── What We Do Darkening Effect ───────── */
  const whatWeDoSection = document.getElementById('what-we-do');
  const whatWeDoOverlay = document.querySelector('.what-we-do__overlay');

  if (whatWeDoSection && whatWeDoOverlay) {
    window.addEventListener('scroll', () => {
      const rect = whatWeDoSection.getBoundingClientRect();
      const windowH = window.innerHeight;

      // We want to fade the header as the boxes come up from below. 
      // The sticky title is at top: 15vh. Let's start the fade when 
      // the top of `.what-we-do` hits the top of the viewport (rect.top <= 0)
      // and max out the fade when we scroll down another 30vh (or 30% of viewport).

      const fadeStart = 0;
      const fadeEnd = -windowH * 0.4; // 40vh into the section scroll

      if (rect.top > fadeStart) {
        whatWeDoOverlay.style.opacity = '0';
      } else if (rect.top <= fadeStart && rect.top >= fadeEnd) {
        // interpolate opacity 0 to 0.85
        let MathProgress = (rect.top - fadeStart) / (fadeEnd - fadeStart);
        let currentOpacity = MathProgress * 0.85;
        whatWeDoOverlay.style.opacity = currentOpacity.toFixed(3);
      } else {
        whatWeDoOverlay.style.opacity = '0.85'; // Maximum darkness
      }
    });
  }

})();
