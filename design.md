# STRYDER — Design System Reference

> This document is the single source of truth for all visual, typographic, and interaction design decisions across the STRYDER landing page and any future pages. **All changes must stay consistent with this file.**

---

## Aesthetic Direction

**Style:** Cinematic Futurist / Tech-noir  
**Mood:** Dark, atmospheric, immersive, high-tech  
**Background:** Full-viewport looping video with dark gradient overlay  

---

## Typography

| Role | Font Family | Weight | Source |
|------|-------------|--------|--------|
| **Display / Headings** | `Syne` | 700–800 (Bold/ExtraBold) | Google Fonts |
| **Body / UI** | `Inter` | 300–500 (Light–Medium) | Google Fonts |

### Heading Scale

| Element | Size (desktop) | Size (mobile) | Weight | Letter-spacing |
|---------|---------------|---------------|--------|----------------|
| Hero title (`h1`) | `clamp(4rem, 10vw, 9rem)` | auto via clamp | 800 | `0.08em` |
| Intro label | `0.875rem` | `0.75rem` | 400 | `0.3em` |
| Description | `1.125rem` | `1rem` | 300 | `0.02em` |

---

## Color Palette

All colors are defined as CSS custom properties on `:root`.

### Core Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-bg` | `#000000` | Page background (behind video) |
| `--color-overlay-start` | `rgba(0,0,0,0.7)` | Top of video overlay gradient |
| `--color-overlay-end` | `rgba(0,0,0,0.5)` | Bottom of video overlay gradient |

### Text Gradient System

| Token | Value | Usage |
|-------|-------|-------|
| `--gradient-text-start` | `#a8ff78` | Gradient text — lime green |
| `--gradient-text-end` | `#78ffd6` | Gradient text — mint |
| `--gradient-accent-start` | `#00ff87` | Accent gradient — emerald |
| `--gradient-accent-end` | `#60efff` | Accent gradient — cyan |

### Text Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--text-primary` | `rgba(255,255,255,0.95)` | High-emphasis text |
| `--text-secondary` | `rgba(255,255,255,0.7)` | Body / descriptions |
| `--text-muted` | `rgba(255,255,255,0.45)` | Captions, meta |
| `--text-label` | `--gradient-text-start` | Small labels like "introducing" |

### Glass / Surface Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--glass-bg` | `rgba(255,255,255,0.05)` | Glassmorphism fill |
| `--glass-bg-hover` | `rgba(255,255,255,0.1)` | Glass hover state |
| `--glass-border` | `rgba(0,255,135,0.15)` | Glass border (green tint) |
| `--glass-border-hover` | `rgba(0,255,135,0.35)` | Glass border hover |
| `--glass-blur` | `16px` | Backdrop blur radius |

---

## Glassmorphism Specification

```css
.glass-btn {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 9999px;       /* pill shape */
  color: var(--text-primary);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-btn:hover {
  background: var(--glass-bg-hover);
  border-color: var(--glass-border-hover);
  box-shadow: 0 0 30px rgba(0, 255, 135, 0.15);
}
```

**Rules for all glass elements:**
- Always use `backdrop-filter: blur()` — never fake blur with opacity alone
- Border must have a subtle green tint to tie into the gradient system
- Hover states increase opacity + add outer glow (`box-shadow`)
- Always use `border-radius: 9999px` for buttons (pill), `1rem` for cards

---

## Video Background

- **Source:** `assets/video/bg.mp4`
- **Attributes:** `autoplay`, `muted`, `loop`, `playsinline`
- **Positioning:** `position: fixed; object-fit: cover; width: 100%; height: 100%;`
- **Seamless Loop:** JS listener resets `currentTime` to `0` when within 0.3s of video end
- **Overlay:** Semi-transparent gradient overlay to guarantee text readability

---

## Spacing Rhythm

| Token | Value |
|-------|-------|
| `--space-xs` | `0.25rem` |
| `--space-sm` | `0.5rem` |
| `--space-md` | `1rem` |
| `--space-lg` | `1.5rem` |
| `--space-xl` | `2rem` |
| `--space-2xl` | `3rem` |
| `--space-3xl` | `4rem` |

---

## Motion / Animation

| Animation | Duration | Easing | Purpose |
|-----------|----------|--------|---------|
| Fade-in up (intro label) | `0.8s` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entry sequence |
| Fade-in up (heading) | `1.0s` | same, `0.2s` delay | Entry sequence |
| Fade-in up (description) | `1.0s` | same, `0.4s` delay | Entry sequence |
| Fade-in up (button) | `0.8s` | same, `0.6s` delay | Entry sequence |
| Button hover glow | `0.3s` | `ease` | Interaction feedback |

**Philosophy:** One strong entrance sequence. Sparse, purposeful motion. No decorative looping animations on text.

---

## Responsive Breakpoints

| Breakpoint | Width | Adjustments |
|------------|-------|-------------|
| Mobile | `≤ 600px` | Heading scales down via `clamp()`, padding reduces, description narrows |
| Tablet | `601–1024px` | Moderate scaling |
| Desktop | `> 1024px` | Full sizing |

---

## File Structure

```
STYRDER_AI_REAL/
├── index.html          # Main landing page
├── styles.css          # Design system + page styles
├── script.js           # Video loop handler + animations
├── design.md           # This file — design reference
├── assets/
│   └── video/
│       └── bg.mp4      # Background video
└── README.md
```

---

## Consistency Rules

1. **Never** use colors outside the tokens defined above
2. **Always** use Syne for headings and Inter for body — no exceptions
3. **Always** apply the gradient to primary heading text, not solid colors
4. **All** interactive elements use glassmorphism — no solid-fill buttons
5. **Keep** the dark overlay on the video — never remove it
6. **Match** any new section or page to this gradient/glass/dark system
