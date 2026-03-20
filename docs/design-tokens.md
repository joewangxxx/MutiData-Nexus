# Design Tokens

Status: `review_pending`
Owner: `designer`
Last Updated: `2026-03-18`

This document defines the shared dashboard token system for MutiData-Nexus. It is intended as a practical starting point for the future Next.js + React implementation without writing UI code.

## Token Strategy

- Use semantic tokens first. Components should read from meaning-based values, not raw hex colors.
- Keep one visual system across annotator and manager views. Role differences should come from content and emphasis, not separate themes.
- Support light and dark mode from the same token set.
- Keep dense data readable. Tables, cards, charts, and workflow views must remain legible when the screen is full of status information.
- Publish tokens in a format that can map cleanly to CSS variables or a theme object later.

## Token Groups

| Group | Purpose | Notes |
|-------|---------|-------|
| Color | Surfaces, text, semantic states, charts | Use token names like `bg`, `surface`, `text`, `status`, and `chart`. |
| Typography | Font families, scale, and weight | Keep body text readable and use tabular figures for metrics. |
| Spacing | Layout rhythm and component padding | Base the scale on 4px and 8px steps. |
| Radius | Corner consistency | Use slightly rounded corners, not pill-heavy branding. |
| Border | Dividers, outlines, focus states | Use borders to support hierarchy, not to decorate every surface. |
| Elevation | Layering for cards, drawers, and modals | Keep shadows subtle so data remains the focus. |
| Motion | Transition timing and state change behavior | Motion should explain state change, not distract from it. |
| Data visualization | Series colors and status mapping | Charts must stay accessible and label-driven. |
| Layout | Shell widths, rails, and dense row heights | Gives the FE team a stable starting point for dashboard composition. |

## Color System

The palette should feel operational, calm, and high-contrast. Teal and blue carry primary emphasis, while amber and red carry attention and risk. Avoid purple-heavy defaults.

### Light Theme

| Token | Value | Usage |
|-------|-------|-------|
| `bg.canvas` | `#F8FAFC` | App background |
| `surface.default` | `#FFFFFF` | Standard cards and panels |
| `surface.raised` | `#FFFFFF` | Modals, drawers, focused cards |
| `surface.subtle` | `#EEF2F7` | Subpanels, table headers, quiet sections |
| `border.default` | `#D6DDE8` | Standard dividers |
| `border.strong` | `#A9B4C4` | Emphasis borders, selected regions |
| `text.primary` | `#0F172A` | Main body text |
| `text.secondary` | `#475569` | Supporting text |
| `text.tertiary` | `#64748B` | Hints, metadata, subdued labels |
| `text.inverse` | `#F8FAFC` | Text on dark or filled surfaces |
| `primary.default` | `#0F766E` | Primary action and active state |
| `primary.hover` | `#115E59` | Hover state |
| `primary.subtle` | `#CCFBF1` | Soft background, badges, selection fill |
| `secondary.default` | `#1D4ED8` | Links, secondary emphasis, project context |
| `accent.default` | `#D97706` | Attention, highlights, callouts |
| `success.default` | `#15803D` | Approved, complete, healthy |
| `warning.default` | `#B45309` | At risk, needs attention |
| `danger.default` | `#B91C1C` | Critical, failed, blocked by issue |
| `info.default` | `#0369A1` | Informational signals |
| `focus.default` | `#0EA5E9` | Keyboard focus ring and focus outline |

### Dark Theme

| Token | Value | Usage |
|-------|-------|-------|
| `bg.canvas` | `#0B1220` | App background |
| `surface.default` | `#111827` | Standard cards and panels |
| `surface.raised` | `#172033` | Modals, drawers, focused cards |
| `surface.subtle` | `#1E293B` | Subpanels, table headers, quiet sections |
| `border.default` | `#243244` | Standard dividers |
| `border.strong` | `#334155` | Emphasis borders, selected regions |
| `text.primary` | `#E5EEF8` | Main body text |
| `text.secondary` | `#94A3B8` | Supporting text |
| `text.tertiary` | `#64748B` | Hints, metadata, subdued labels |
| `text.inverse` | `#0B1220` | Text on light fills |
| `primary.default` | `#2DD4BF` | Primary action and active state |
| `primary.hover` | `#5EEAD4` | Hover state |
| `primary.subtle` | `#103A37` | Soft background, badges, selection fill |
| `secondary.default` | `#60A5FA` | Links, secondary emphasis, project context |
| `accent.default` | `#F59E0B` | Attention, highlights, callouts |
| `success.default` | `#4ADE80` | Approved, complete, healthy |
| `warning.default` | `#FBBF24` | At risk, needs attention |
| `danger.default` | `#F87171` | Critical, failed, blocked by issue |
| `info.default` | `#38BDF8` | Informational signals |
| `focus.default` | `#67E8F9` | Keyboard focus ring and focus outline |

### Status and Role Mapping

Status colors should always be paired with labels or icons. Color alone is never enough to communicate meaning.

| State | Suggested token |
|-------|------------------|
| Pending | `text.tertiary` or a neutral slate token |
| In progress | `secondary.default` |
| Under review | `info.default` |
| Blocked | `accent.default` or `warning.default` depending on severity |
| Approved | `success.default` |
| Complete | `primary.default` |
| At risk | `warning.default` |
| Critical | `danger.default` |

## Typography

Use a technical, readable type system that feels precise without looking sterile.

| Token | Value | Usage |
|-------|-------|-------|
| `font.sans` | `IBM Plex Sans, Segoe UI, sans-serif` | Body text, labels, tables, shell navigation |
| `font.display` | `Space Grotesk, IBM Plex Sans, sans-serif` | Page titles, prominent section headers |
| `font.mono` | `IBM Plex Mono, SFMono-Regular, monospace` | IDs, timestamps, audit data, workflow logs |

### Type Scale

| Token | Size / Line height | Usage |
|-------|--------------------|-------|
| `text.xs` | `12 / 16` | Metadata, badges, table utilities |
| `text.sm` | `14 / 20` | Secondary copy, labels, compact help text |
| `text.md` | `16 / 24` | Default body text |
| `text.lg` | `18 / 28` | Section intros, key metrics |
| `text.xl` | `20 / 28` | Card titles, prominent labels |
| `text.2xl` | `24 / 32` | Page titles in dense dashboard contexts |
| `text.3xl` | `28 / 36` | Landing headers and important summaries |
| `text.4xl` | `36 / 44` | Rare hero treatment only |

### Weight and Number Rules

- Use `400` for body text, `500` for labels, `600` for headings, and `700` only for emphasis.
- Use tabular numbers for counts, SLA timers, timestamps, and chart axes.
- Avoid all-caps body text. Reserve uppercase for small labels only if it improves scanability.

## Spacing and Layout

The spacing scale should support dense dashboards without collapsing readability.

| Token | Value |
|-------|-------|
| `space.1` | `4px` |
| `space.2` | `8px` |
| `space.3` | `12px` |
| `space.4` | `16px` |
| `space.5` | `20px` |
| `space.6` | `24px` |
| `space.8` | `32px` |
| `space.10` | `40px` |
| `space.12` | `48px` |
| `space.16` | `64px` |

### Layout Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `layout.sidebar-width` | `280px` | Default left rail width |
| `layout.sidebar-collapsed` | `84px` | Compact rail mode |
| `layout.topbar-height` | `64px` | Persistent shell header |
| `layout.context-rail-width` | `320px` | Evidence and context drawer |
| `layout.drawer-width` | `384px` | Modals and slideovers |
| `layout.content-max-width` | `1280px` | Main content max width |
| `layout.page-max-width` | `1440px` | Wide dashboard pages |
| `layout.dense-row-height` | `44px` | Compact list rows |
| `layout.table-row-height` | `48px` | Standard table rows |

## Radius and Border

| Token | Value | Usage |
|-------|-------|-------|
| `radius.sm` | `6px` | Inputs, chips, tags |
| `radius.md` | `10px` | Standard cards and panels |
| `radius.lg` | `14px` | Larger panels, drawers, modals |
| `radius.xl` | `18px` | Rare, for hero summary surfaces |
| `border.hairline` | `1px` | Standard separators |
| `border.focus` | `2px` | Keyboard focus and selection outlines |

The product should feel crisp and controlled, not pill-heavy or overly soft.

## Elevation

Shadows should support hierarchy without making the interface feel heavy.

| Token | Value | Usage |
|-------|-------|-------|
| `elevation.1` | `0 1px 2px rgba(15, 23, 42, 0.06)` | Subtle cards |
| `elevation.2` | `0 4px 12px rgba(15, 23, 42, 0.08)` | Hovered cards, dropdowns |
| `elevation.3` | `0 8px 24px rgba(15, 23, 42, 0.12)` | Sheets and drawers |
| `elevation.4` | `0 20px 48px rgba(15, 23, 42, 0.16)` | High-emphasis overlays |

In dark mode, keep elevation lighter and rely more on borders and surface shifts than on large shadows.

## Motion

Motion should be calm, short, and meaningful.

| Token | Value | Usage |
|-------|-------|-------|
| `motion.fast` | `120ms` | Hover and press feedback |
| `motion.standard` | `180ms` | Common transitions |
| `motion.slow` | `240ms` | Drawer or panel entrance |
| `motion.emphasis` | `320ms` | Larger state changes, such as page segment transitions |

Guidelines:

- Use transform and opacity, not layout-changing animation.
- Keep motion interruptible.
- Respect reduced-motion preferences by shortening or removing non-essential transitions.
- Use motion to show cause and effect, such as opening a drawer from its trigger or expanding a run step into detail.

## Data Visualization

Charts and trend modules must be readable in both themes and in compact dashboard cards.

| Token | Suggested color |
|-------|-----------------|
| `chart.series.1` | `#1D4ED8` |
| `chart.series.2` | `#0F766E` |
| `chart.series.3` | `#15803D` |
| `chart.series.4` | `#D97706` |
| `chart.series.5` | `#B91C1C` |
| `chart.series.6` | `#0369A1` |
| `chart.series.7` | `#0E7490` |
| `chart.series.8` | `#64748B` |

### Chart Rules

- Do not rely on color alone to distinguish series.
- Keep grid lines subtle and low contrast.
- Always show labels, legends, or direct annotations for critical data.
- Use the same color mapping for the same semantic state across dashboard cards and charts.

## Accessibility Baseline

At minimum, the token system must support:

- Contrast of at least 4.5:1 for body text and 3:1 for large text and non-text UI states.
- Visible focus treatment that is consistent across all interactive elements.
- Disabled states that combine color, opacity, and semantic disabled behavior.
- Touch and click targets at or above 44 by 44 pixels where applicable.
- Reduced-motion behavior for users who request it.
- Dense-data readability, including tabular numerals and clear visual separation between rows and panels.

## Next.js + React Guidance

- Keep tokens shared across annotator and manager routes.
- Make layout decisions through shared shell tokens rather than screen-by-screen values.
- Use semantic state names so components can consume the same values across cards, tables, drawers, and charts.
- Treat the design token set as the source of truth for future frontend work, not as a one-off styling reference.

