---
name: saas-sidebar-redesign
description: Redesign a Vue 3 app's shell into a modern SaaS-style layout with a vertical left sidebar instead of a top nav bar, consistent spacing tokens, and a polished professional look. Use when asked to replace the top navigation with a sidebar, restyle the app shell, or modernize the look and spacing of Vue views in this project.
---

# SaaS Sidebar Redesign

Turns the top-nav Vue app into a left-sidebar application shell with consistent spacing and a restrained, professional visual style. The work is mostly in the shell (`client/src/App.vue`) and a shared set of design tokens. Views are normalized to those tokens, not rewritten.

## Ground rules

1. **Delegate `.vue` edits to vue-expert.** The project's CLAUDE.md makes this mandatory for any significant `.vue` change. Brief vue-expert with the spec in this file. Do not write the component code yourself.
2. **Behavior does not change.** Keep every route path, `router-link` target, i18n key, API call, and filter. This is a visual and layout change. If a view needs a behavior change to fit the new layout, stop and ask.
3. **Keep the existing palette.** CLAUDE.md's design system is slate/gray (`#0f172a`, `#64748b`, `#e2e8f0`) with green/blue/yellow/red for status. Do not introduce a new brand color unless the user asks.
4. **No emojis in the UI.** Use text labels, or inline SVG icons if the project has them.
5. **Document non-obvious logic.** Any non-obvious CSS or JS logic gets a comment explaining why (for example, why the sidebar switches to a drawer at a given breakpoint, or why a `z-index` is set). Obvious declarations do not need comments.

## Step 1: Inventory the current shell

Read these before designing anything:

- `client/src/App.vue`: the top nav (`router-link` items, the active-class logic, the `ProfileMenu` and `LanguageSwitcher` placement, and the global styles).
- `client/src/main.js`: the route table. The sidebar must link to exactly these routes.
- `client/src/locales/en.js` and `ja.js`: the `nav.*` keys. Sidebar labels must come from these keys, not hard-coded strings.
- `client/src/views/*.vue`: note any hard-coded padding, margins, or widths that would fight a new shell. Do not restyle the views yet.

Record the current nav items and their order. The sidebar will group them, but it must not drop or rename any.

## Step 2: Define design tokens

Put the tokens in `:root` in `client/src/App.vue`, which is where project styles live per CLAUDE.md.

**Spacing scale** (4px base, use only these values):

```css
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;
--space-4: 16px;  --space-5: 24px;  --space-6: 32px;  --space-7: 48px;
```

**Layout:**

```css
--sidebar-width: 248px;
--sidebar-collapsed: 64px;
--content-max: 1280px;
--radius: 8px;
```

**Color:** reuse the slate palette. Add `--surface` (white), `--surface-muted` (`#f8fafc`), `--border` (`#e2e8f0`), `--text` (`#0f172a`), `--text-muted` (`#64748b`), and `--accent` (blue, for the active nav item).

**Type:** one system font stack, a body size of 14px or 15px, headings with tighter letter-spacing (`-0.01em` to `-0.02em`), and a line height of about 1.5.

**Elevation:** one soft shadow for cards and the drawer, for example `0 1px 2px rgba(15, 23, 42, 0.06)`. Avoid stacking multiple shadows.

## Step 3: Design the shell

Use a CSS grid on the app root, not absolute positioning:

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: 100vh;
}
```

The `minmax(0, 1fr)` matters: without the `0`, wide tables inside the content area push the layout off screen.

**Sidebar** (`<nav aria-label="Main">`):
- Sticky or fixed to the viewport height (`position: sticky; top: 0; height: 100vh; overflow-y: auto`).
- Top: brand block (app name only, no logo asset unless one exists).
- Middle: grouped nav. Suggested groups, using only existing routes:
  - **Overview:** Dashboard (`/`)
  - **Operations:** Inventory, Orders, Restocking
  - **Planning:** Demand, Backlog
  - **Finance:** Spending, Reports
  Group labels are small uppercase muted text. Each item is a full-width row with an icon-or-dot slot, label, and `space-2` / `space-3` padding.
- Active item: `aria-current="page"`, a 2px accent bar on the left edge, and a subtle background tint. Derive the active state from `$route.path` as the current code does, and keep the exact-match rule for `/`.
- Bottom: `ProfileMenu` and `LanguageSwitcher`, kept where the top nav had them, now stacked.

**Content area:**
- A slim page header (title plus optional actions), a max-width container of `--content-max`, and `space-5` padding on the page.
- Do not add a second top nav bar. The header is for the page title only.

**Collapsing (optional, only if asked or cheap to add):** a toggle that shrinks the sidebar to `--sidebar-collapsed` and shows icons only. Store the state in `localStorage`. Add a comment explaining the storage key and why it is persisted.

## Step 4: Responsive behavior

- **Above 1024px:** fixed sidebar, as above.
- **Below 1024px:** the sidebar becomes an off-canvas drawer. A menu button in the header opens it. The drawer overlays the content with a backdrop.
- Drawer behavior: close on backdrop click, on Escape, and after navigating to a route. Move focus into the drawer when it opens and return it to the menu button when it closes.
- Comment the breakpoint: it is tied to the point where the sidebar plus a table stops fitting, not to a device size.

## Step 5: Normalize the views

Do this only after the shell is working.

- Replace hard-coded `padding`, `margin`, and `gap` values in views with the spacing tokens. Map values to the nearest token and note any that do not map cleanly.
- Give cards and tables the shared `--radius`, `--border`, and `--surface` values.
- Do not change markup structure, classes that JavaScript relies on, or `v-for` keys.
- Keep `.num` and other existing utility classes working.

## Step 6: Accessibility

- A skip link as the first focusable element, pointing to the main content.
- `<nav>` with an `aria-label`. `aria-current="page"` on the active link.
- Visible `:focus-visible` outlines on nav links, the menu button, and the drawer.
- Color contrast of at least 4.5:1 for body text and nav labels.
- Respect `prefers-reduced-motion`: disable the drawer slide and any transitions.

## Step 7: Verify

Run these in order and fix failures before reporting.

1. **Build:** `cd client && npm run build` must pass with no errors.
2. **Dev server:** confirm `http://localhost:3000` responds. If it is not running, start it with `npm run dev` in `client/`.
3. **Browser check with Playwright MCP** (`mcp__playwright__*`), against `http://localhost:3000`:
   - At 1440px wide: navigate to each route in the sidebar, take a snapshot, and confirm the active item matches the page.
   - At 390px wide: open the drawer, navigate, and confirm it closes.
   - Check the console for errors and warnings after each route.
   - Take a screenshot of the dashboard at 1440px and check it visually for alignment, spacing, and overflow.
4. **Route parity:** every route in `main.js` is reachable from the sidebar, and no sidebar link points at a missing route.
5. **Behavior parity:** filters and data on the Dashboard, Orders, and Inventory pages still load and respond as before.

## Step 8: Report

Give the user:
- Files changed, and which parts were done by vue-expert.
- The tokens added and where they live.
- Routes and their sidebar groups.
- Breakpoints and what happens at each.
- The verification results, including any screenshot you took, and any check you could not run.

## Checklist

- [ ] Every `.vue` change went through vue-expert
- [ ] No route, i18n key, or API call changed
- [ ] Spacing uses only the scale tokens
- [ ] No second top nav bar remains
- [ ] Sidebar uses `<nav aria-label>` and `aria-current`
- [ ] Drawer closes on Escape, backdrop, and navigation
- [ ] Non-obvious CSS and JS logic has a comment
- [ ] No emojis in the UI
- [ ] `npm run build` passes
- [ ] Desktop and mobile checked in the browser, console clean
