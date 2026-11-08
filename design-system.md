# FeedbackIQ Design System Specification (Linear & Stripe Inspired)

> Source of Truth for FeedbackIQ Frontend Architecture & Visual Language.
> Linked Figma Design File: [FeedbackIQ — Production Design System & UI](https://www.figma.com/design/6mF7EEC2F41ydZIn0UiCZs)
> Linked FigJam Architecture Board: [FeedbackIQ — Design System Architecture](https://www.figma.com/board/oRJ3BNnUDbCBCAebTqSVt4)

---

## 🎨 Color Palette & Elevation

| Token | Hex Value | Usage |
|---|---|---|
| `canvas` | `#080B11` | Primary screen background (deep charcoal) |
| `surface` | `#0E131F` | Primary card, sidebar, and container background |
| `surface-raised`| `#141A29` | Elevated cards, dropdowns, modals, and tooltips |
| `surface-hover` | `#1A2234` | Hover states on interactive rows and buttons |
| `border-subtle` | `rgba(255, 255, 255, 0.06)` | Standard component dividing lines (hairline 1px) |
| `border-muted`  | `#1E2638` | Default card borders |
| `border-focus`  | `#3B4863` | Focused inputs and active card outlines |
| `text-primary`  | `#F8FAFC` | Primary headings, titles, and key metrics |
| `text-secondary`| `#94A3B8` | Subtitles, descriptions, and labels |
| `text-muted`    | `#64748B` | Footers, timestamps, and placeholder copy |
| `accent-violet` | `#7C3AED` | Primary brand accent and action buttons |
| `accent-indigo` | `#6366F1` | Secondary accents and neutral tags |
| `accent-cyan`   | `#06B6D4` | AI highlights, active indicators, and sparklines |
| `status-emerald`| `#10B981` | Positive sentiment and healthy status |
| `status-rose`   | `#F43F5E` | Negative sentiment, critical bugs, and P0 alerts |
| `status-amber`  | `#F59E0B` | High severity, warnings, and star ratings |

---

## 🔤 Typography Ramp

- **Primary Font Family:** `Plus Jakarta Sans`, sans-serif (Headings, KPIs, Brand)
- **Body Font Family:** `Inter`, -apple-system, BlinkMacSystemFont, sans-serif (Body text, Tables)
- **Monospace Family:** `JetBrains Mono`, monospace (IDs, counts, timestamps, JSON, tokens)

### Hierarchy
- **Display 1 (Dashboard Titles):** `24px (1.5rem)` / Semibold `600` / Tracking `-0.025em`
- **Heading 2 (Card Titles):** `14px (0.875rem)` / Bold `700` / Tracking `-0.01em`
- **Body Regular:** `13px (0.8125rem)` / Regular `400` / Line height `1.5`
- **Caption / Meta:** `11px (0.6875rem)` / Medium `500` / Text secondary
- **Micro Badge:** `10px (0.625rem)` / Semibold `600` / Uppercase tracking `0.05em`

---

## 📐 Spacing & Geometry

- **Border Radius:**
  - Badges & Pills: `6px` (`rounded-md`)
  - Buttons & Inputs: `8px` (`rounded-lg`)
  - Cards & Panels: `12px` (`rounded-xl`)
  - Large Modals: `16px` (`rounded-2xl`)
  - *Strictly avoid:* Cartoonish oversized rounded corners (`rounded-3xl` or excessive `32px`).
- **Dividers & Borders:**
  - Always `1px` solid hairlines with low opacity (`border-white/[0.06]` or `#1E2638`).
- **Shadows:**
  - Crisp, shallow drop shadows: `box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)`.
  - Micro focus rings: `ring-1 ring-violet-500/50`.

---

## 🧩 Component System

1. **Navigation Sidebar:**
   - Slim 240px fixed width with workspace switcher.
   - Categorized sections: `WORKSPACE`, `INTELLIGENCE`, `MANAGEMENT`.
   - Subtle active background (`bg-white/[0.06] text-white`).
   - Compact count badges (`bg-slate-800 text-slate-300 font-mono text-[10px]`).
2. **KPI Metric Card:**
   - Compact height, value in 28px bold, contextual delta pill, subtle category label.
3. **Data Visualization (Recharts):**
   - Clean dark tooltips (`bg-[#0E131F] border border-[#1E2638] text-xs`).
   - Slim donut with centered total and horizontal legend.
   - Smooth curved line chart with area fill gradient.
   - Horizontal bars with priority status color coding.
4. **Data Tables:**
   - 40px row height for high information density.
   - Hover row highlight with cursor pointer.
   - Dot indicator sentiment badges.
   - Slide-over drawer for inspection.
5. **Conversational Assistant:**
   - Message bubbles with hairline border.
   - Grounded quote citations in dedicated monospace quote cards.
   - Referenced theme tags.
