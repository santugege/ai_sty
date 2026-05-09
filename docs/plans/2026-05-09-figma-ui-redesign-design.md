# Figma UI Redesign Design

## Goal

Create a new Figma concept screen for the image toolbox as a professional ecommerce image command center.

## Context

The current app is a Next.js and Tailwind CSS product image generation workbench. The active home screen lives in `frontend/src/components/home-product-workbench.tsx`, with a dark studio layout, a central canvas, a right inspector, and a bottom prompt composer. Several visible Chinese strings are currently mojibake, so the redesign should restore readable Chinese copy and make the product feel trustworthy.

## Direction

Use a light, operational interface instead of another neon studio. The screen should feel like a production tool for ecommerce operators: calm, precise, fast to scan, and centered around the generated product image.

## Layout

- Left rail: product identity, workspace navigation, and compact task status.
- Main canvas: large preview area with a polished empty state and a result preview state.
- Left composer panel: upload area, prompt, product selling points, and preservation notes.
- Right strategy panel: platform preset, image purpose, aspect ratio, scene, tone, and safety constraints.
- Bottom action bar: primary generation button, selected configuration summary, and error/status space.

## Visual System

- Background: warm light gray with crisp panels, not beige-heavy.
- Accent colors: coral for primary action, teal for active generation state, graphite for text, and restrained amber for warnings.
- Corners: mostly 6-8px radius for a professional tool feel.
- Typography: readable Chinese-first sans type with clear hierarchy.
- Components: segmented controls, icon buttons, upload drop zone, text areas, parameter chips, and an output canvas.

## States

- Empty state: shows upload guidance and sample composition guides without looking like a marketing hero.
- Generated state: centers the image, shows a revised prompt log, and preserves the same parameter panels.
- Error state: appears inline in the bottom action bar and near invalid controls.

## Success Criteria

- The Figma file contains a complete desktop first screen that can guide frontend implementation.
- Chinese text is readable and concise.
- The interface is visually cleaner, more useful, and more professional than the current dark UI.
- The layout clearly maps back to the existing app workflow: upload, prompt, configure, generate, inspect result.
