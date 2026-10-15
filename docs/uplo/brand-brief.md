CI Pic & Brief

ได้เลยครับ ผมจะเขียนเป็น **English Design & Development Brief** ที่คุณสามารถส่งให้ Front-End Developer หรือ Copy ไปให้ AI Coding Assistant (เช่น Cursor, Claude Code หรือ Codex) ได้ทันที

ผมจะยึด **UPLO Brand Identity เวอร์ชันล่าสุด** ที่เราเพิ่งปรับให้ Signal Lime โดดเด่นขึ้น โดยยังรักษาความรู้สึก Industrial, Innovative, Premium และ Financial Technology ไว้

---

# UPLO — Front-End Design & Brand Implementation Brief
**Version 1.0 | Brand Identity & UI Guidelines**

## 1. Project Overview

**Brand Name:** UPLO  
**Industry:** Circular Finance × Industrial Innovation × Web3  
**Tagline:** Today's Capital. Tomorrow's Breakthroughs.

### About UPLO

UPLO is a blockchain-enabled financial infrastructure platform that connects revenue-generating battery recycling businesses with emerging technologies and research opportunities.

Our platform creates a continuous cycle of capital and innovation by facilitating commercial financing, allocating a defined portion of platform revenue toward research development, and supporting the commercialization of promising technologies.

### Brand Positioning

UPLO should be perceived as a **next-generation financial infrastructure company**, not a conventional cryptocurrency platform or environmental organization.

Our visual identity combines the credibility of institutional finance, the sophistication of industrial technology, and the progressive nature of innovation.

**Brand keywords:**
Innovative · Industrial · Trustworthy · Intelligent · Progressive · Minimal

---

## 2. Core Design Philosophy

### Industrial Innovation Minimalism

The overall design language should balance three characteristics:

**01 — Industrial Strength**

Use structured layouts, bold typography, geometric elements, and material-inspired aesthetics to establish credibility.

**02 — Technological Innovation**

Introduce vibrant Signal Lime accents, subtle interactions, precise data visualizations, and modern UI patterns to convey technological advancement.

**03 — Financial Trust**

Maintain excellent readability, clear information hierarchy, transparent transaction states, and a professional interface.

### Design Principles

- Prioritize simplicity, clarity, and usability.
- Maintain generous whitespace and consistent spacing.
- Use bold typography to communicate important information.
- Emphasize financial transparency and measurable impact.
- Avoid unnecessary decorative elements.
- Ensure all components share a consistent design system.
- Maintain brand consistency across desktop, tablet, and mobile.

**Important:** The final interface should feel like a sophisticated industrial-fintech platform, rather than a generic SaaS dashboard or cryptocurrency exchange.

---

# 3. Color Identity

The following color palette is mandatory and should be implemented as reusable design tokens.

### Primary Color Palette

| Color | Hex Code | Usage |
|---|---|---|
| **Signal Lime** | #D7EB79 | Primary accent, CTAs, active states, selected components |
| **Deep Charcoal** | #1E2320 | Primary text, sidebar, dark surfaces |
| **Mineral Copper** | #B57856 | Secondary accent, industrial highlights |
| **Limestone** | #EDE8DD | Main background, neutral surfaces |
| **Sage Gray** | #A7B8A1 | Secondary information, innovation indicators |
| **Neutral Gray** | #D9D9D6 | Dividers, disabled elements, subtle borders |

### Color Usage Guidelines

**Signal Lime — Primary Brand Accent**

Signal Lime is the most distinctive element of UPLO's updated brand identity.

It should be used prominently for:

- Primary call-to-action buttons
- Active navigation states
- Selected tabs and interactive components
- Financial flow visualization
- Key metrics and highlighted data
- Progress indicators and subtle graphic accents

However, Signal Lime should never overwhelm the interface.

Use it intentionally to guide users toward important actions and information.

**Deep Charcoal — Foundation**

Use Deep Charcoal for:

- Main typography
- Sidebar navigation
- Header elements
- Dark interface sections
- Institutional or financial content requiring visual authority

**Mineral Copper — Industrial Identity**

Mineral Copper represents the physical-material and industrial foundation of UPLO.

Use it selectively for:

- Industrial asset illustrations
- Secondary highlights
- Data visualizations
- Material-related indicators
- Decorative lines and geometric details

Copper should complement Signal Lime rather than compete with it.

**Limestone — Main Background**

Avoid pure white backgrounds across the entire interface.

Limestone creates a warmer, more sophisticated appearance that distinguishes UPLO from conventional financial dashboards.

White may still be used for cards and elevated surfaces.

### Recommended Visual Balance

- 50–60% Limestone and neutral backgrounds
- 20–25% Deep Charcoal
- 10–15% Signal Lime
- 5–10% Mineral Copper and supporting colors

These are approximate visual proportions, not strict mathematical requirements.

### Accessibility

Maintain WCAG-compliant text contrast wherever possible.

In particular, use **Deep Charcoal text on Signal Lime buttons** rather than white text.

Do not rely on color alone to communicate financial or transaction statuses.

---

# 4. Logo Guidelines

### Primary Logo

Use the provided **UPLO wordmark** as the primary brand asset.

The logo consists of:

- Geometric uppercase typography
- Bold industrial letterforms
- A distinctive segmented circular “O”
- Signal Lime and Deep Charcoal as the primary logo colors

### Logo Rules

1. Use the original supplied logo asset whenever possible.
2. Preserve its proportions and typography.
3. Maintain sufficient whitespace around the logo.
4. Never stretch, distort, or recreate the logo using a different font.
5. Avoid applying additional shadows, gradients, outlines, or decorative effects.
6. Use the standalone circular mark only when an approved icon asset is available.

**Important:** Do not generate or redesign the UPLO logo. The provided transparent PNG is the reference asset.

If a dark-background variation is needed, create it from approved brand assets rather than inventing a new logo.

---

# 5. Typography System

### Primary Typeface: Space Grotesk

Use for:

- Hero headlines
- Section headings
- Key financial metrics
- Important labels
- Marketing and brand communications

Recommended weights: Medium, SemiBold, Bold.

### Secondary Typeface: Inter

Use for:

- Body text
- Navigation
- Buttons
- Forms
- Tables
- Financial information
- Dashboard components

Recommended weights: Regular, Medium, SemiBold.

### Thai Typeface: Noto Sans Thai

Use whenever Thai-language content is displayed.

### Typography Hierarchy

| Element | Desktop Size | Weight |
|---|---|---|
| Hero Heading | 56–72px | SemiBold |
| Page Heading | 36–48px | SemiBold |
| Section Heading | 24–32px | SemiBold |
| Card Heading | 18–20px | Medium |
| Body Text | 14–16px | Regular |
| Supporting Text | 12–14px | Regular |
| Financial Metrics | 28–40px | SemiBold |

Use responsive typography scaling on smaller screens.

Keep line heights comfortable and avoid excessive letter spacing.

For financial information, use tabular numerals to maintain consistent alignment.

---

# 6. Layout & Component Design

### Layout

Use a structured, grid-based layout with clear visual hierarchy.

Recommended:

- 12-column responsive grid
- 8px spacing system
- 24–32px spacing between major dashboard components
- 8–12px border radius
- Subtle borders
- Minimal shadows

### Cards

Cards should be clean and structured.

Preferred styling:

- White or soft neutral surface
- Thin neutral border
- 8–12px radius
- Minimal or no shadow
- Clear distinction between title, value, and supporting information

Avoid excessive nested cards.

### Buttons

**Primary Button**
- Signal Lime background
- Deep Charcoal text
- Medium or SemiBold typography
- 8px border radius
- Subtle hover and pressed states

**Secondary Button**
- Transparent or neutral background
- Deep Charcoal border and text

**Destructive Action**
- Use a dedicated accessible warning or error color.
- Do not use Signal Lime for destructive actions.

### Navigation

Use a Deep Charcoal sidebar for the main dashboard.

The active navigation item should use Signal Lime as its primary highlight.

Navigation icons should be simple, geometric, and consistent in stroke width.

### Data Visualization

Charts should follow UPLO's brand identity.

Recommended colors:

- Signal Lime — Primary data
- Mineral Copper — Secondary data
- Sage Gray — Supporting data
- Deep Charcoal — Labels and axes

Avoid generic rainbow-colored charts.

Always include clear labels, units, legends, and relevant time periods.

---

# 7. Product UI Structure

The interface should prioritize capital movement, commercial assets, and innovation development.

### Main Navigation

| Section | Description |
|---|---|
| Overview | Platform performance and capital flow |
| Commercial Finance | Financing opportunities backed by commercial activities |
| Innovation Pool | Capital allocated toward emerging technologies |
| Research Pipeline | TRL 4–6 research opportunities |
| Validation | Scientific milestones and verification records |
| Transactions | On-chain financial activity |
| Impact | Commercial and innovation outcomes |

### Homepage

**Hero Headline:**

**Today's Capital.**  
**Tomorrow's Breakthroughs.**

**Supporting Copy:**

Connecting commercial battery recycling with the next generation of circular innovation.

**Primary CTA:** Explore Opportunities

**Secondary CTA:** How It Works

### Dashboard

The most important visual element should be the **Capital Flow Visualization**.

It should communicate:

**Commercial Assets → Financing → Platform Revenue → Innovation Funding → Research Development**

This flow is the defining feature of UPLO's interface.

Users should immediately understand how existing industrial economic activity can help su