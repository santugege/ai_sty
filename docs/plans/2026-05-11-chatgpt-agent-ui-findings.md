# ChatGPT Agent UI Findings

Date: 2026-05-11

## Initial Retrieval

- `frontend/src/components/agent-image-workbench.tsx` is the `/agent` workbench and uses session-scoped agent APIs.
- `frontend/src/components/product-workbench.tsx` is the product image flow; it submits and renders results in-place.
- `frontend/src/components/app-nav.tsx` defines top-level navigation labels and links, including `ChatGPT 对话` at `/agent`.
- `frontend/src/app/globals.css` defines the current shared visual tokens and panel utilities.
- Existing tests include `frontend/tests/agent-workbench.test.mjs`, with source-level expectations for agent route and nav label.

## Existing Docs

- `docs/plans/2026-05-08-multiturn-image-agent-design.md` says agent workflow is a separate `/api/agent` namespace and the simple product route can remain alongside it.
- `docs/plans/2026-05-10-agent-multi-session-storage-design.md` says `/agent` renders `AgentImageWorkbench`.

## Notes

- Need inspect whether ChatGPT entry currently routes away from the product page, and whether product image exposes route/state logic that can be mirrored by an in-page mode.

## Route And UI Findings

- `frontend/src/app/page.tsx` renders `AppNav` and a compact `ProductWorkbench` in a two-column shell.
- `frontend/src/app/agent/page.tsx` currently returns only `<AgentImageWorkbench />`, so ChatGPT conversation is indeed an isolated full page without the same outer product shell.
- `AgentImageWorkbench` has its own internal left session sidebar, header, scrollable message list, current image context, and bottom composer. It uses hardcoded colors instead of shared `globals.css` tokens.
- `ProductWorkbench` keeps upload, submit, result preview, revised prompt, and errors in the same mounted workbench state. The likely matching logic for ChatGPT is an in-page mode or shared shell that mounts `AgentImageWorkbench` beside the same navigation rather than jumping to a separate visual context.
- `AppNav` already labels `/agent` as `ChatGPT 对话`; clicking it currently changes the route and page shell.
- `globals.css` defines the existing `/agent`-like restrained palette: paper, surface, ink, accent, coral, gold, and shared panel/shadow utilities.
- Billing, admin, and payment return pages already use `AppNav` and the same paper/surface/ink tokens, but their shells repeat markup and use less of the `/agent` full-height workbench structure.
- Login and register are standalone auth cards without `AppNav`, which likely should remain standalone unless "all pages" explicitly includes unauthenticated auth screens.
- `frontend/src/app/tools/[toolId]/page.tsx` uses an older "Studio Matrix" top bar and does not match the current `/agent`/homepage shell. Since non-product tools are rejected, this route is probably legacy but still part of the UI surface.
