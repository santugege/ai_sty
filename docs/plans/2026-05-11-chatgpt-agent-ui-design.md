# ChatGPT Agent UI Design

Date: 2026-05-11

## Goal

Make ChatGPT conversation feel like part of the same product workbench instead of a detached page, and align the app's main pages with the restrained `/agent` visual language.

## Approved Approach

Use a shared app shell with the existing `AppNav` rail and a full-height workbench dock. The product page and ChatGPT page will both render inside that shell. The `/agent` route can remain as the URL for direct access and browser history, but its visual behavior will match the product image flow: same navigation frame, same docked workspace, and in-place conversation state.

## UI Direction

The app should use the `/agent` direction as the source of truth: quiet light surfaces, thin borders, compact controls, dense work-focused layout, restrained accent color, and no marketing-style sections. Login and register keep standalone auth cards but use the same tokens and geometry.

## Implementation Units

- Add a shared `AppShell` component for the authenticated workspace frame.
- Update `/` and `/agent` to render their workbenches inside `AppShell`.
- Update `AgentImageWorkbench` to support a compact embedded variant and use shared design tokens instead of hardcoded colors.
- Move billing, payment return, and admin pages onto `AppShell` where appropriate.
- Leave auth pages standalone but visually aligned.

## Testing

Use source-level frontend tests already present in the repo. Add red tests for the shell contract and ChatGPT route embedding before implementation, then run focused tests and lint/build after changes.
