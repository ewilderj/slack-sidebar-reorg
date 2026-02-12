# AGENTS.md — Slack Reorg Skill

Context for AI agents working in this skill directory.

## What This Is

A Copilot skill that automates Slack sidebar reorganization via Playwright
browser automation. Two phases: Design (extract sidebar → propose layout → refine)
and Execute (diff current vs desired → puppet the UI).

## File Reference

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent-facing instructions (triggers, workflow, commands) |
| `scripts/login` | First-time setup: install Chromium, open browser for SSO |
| `scripts/session_helper.py` | Shared module: session dir paths, Playwright checks |
| `scripts/extract-sidebar` | Playwright: scroll virtualized sidebar → JSON to stdout |
| `scripts/diff-layout` | Compare current JSON vs desired YAML → action plan JSON |
| `scripts/execute-reorg` | Playwright: execute action plan on live Slack |
| `configs/*.yaml` | Per-user layout configs (gitignored — store yours at `~/.slack-reorg/`) |
| `references/DESIGN_GUIDE.md` | Principles for sidebar design |
| `references/PUPPET_STRATEGY.md` | Verified DOM selectors and automation gotchas |

## Session Storage

Sessions are stored in `~/.slack-reorg/sessions/{workspace-hostname}/`.
Auto-derived from `--workspace`.

## Python Environment

All scripts use PEP 723 inline script metadata and are invoked via `uv run`.
No venv setup needed — `uv` resolves dependencies automatically.

The scripts use `#!/usr/bin/env -S uv run --script` shebangs, so they can also
be run directly as `./scripts/login` (but `uv run scripts/login` is preferred
for clarity).

## Execution Workflow

### 1. Set up Python environment
```bash
# No setup needed — uv handles everything via inline script metadata.
# Just ensure uv is installed: https://docs.astral.sh/uv/
```

### 2. Login to Slack
```bash
uv run scripts/login --workspace https://mycompany.slack.com
# Browser opens → complete SSO → wait for sidebar to load → done
```

### 3. Extract current sidebar
```bash
uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > /tmp/sidebar.json
```

### 4. Generate action plan
```bash
uv run scripts/diff-layout \
  --current /tmp/sidebar.json \
  --desired ~/.slack-reorg/layout.yaml \
  > /tmp/action-plan.json
```

### 5. Review the plan
```bash
uv run scripts/execute-reorg --plan /tmp/action-plan.json --dry-run
```

### 6. Execute (with user approval)
```bash
uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com
```

**Timing**: ~5s per channel move. Browser must stay visible (not headless).

### 7. Verify
```bash
uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > /tmp/sidebar-after.json
# Compare before/after
```

## Critical Technical Gotchas

1. **Virtualized sidebar**: Only ~92 items render at once. Scripts scroll
   in 80px steps (items are ~28-36px tall). If a channel isn't found, it may
   need more scroll range.

2. **Duplicate data-qa selector**: `channel_ctx_menu_move` is shared by
   "Edit notifications" AND "Move channel". Scripts find the correct submenu
   trigger by matching text content containing "Move channel".

3. **Interstitial pages**: Some Slack workspaces show a "Launch in app" page
   when opening URLs. Scripts handle it by clicking the "open in browser" link.

4. **URL must be /messages/**: Using `/archives/` triggers extra redirects.

5. **ExternalProtocolDialog**: Chromium flag `--disable-features=ExternalProtocolDialog`
   suppresses "Open in Slack?" system dialog. Already set in all scripts.

6. **ReactModal overlay cleanup**: `<div class="ReactModal__Overlay">` elements
   block pointer events on sidebar items. Scripts check for overlays AND
   `[role="menu"]` before every operation and press Escape until clear.

7. **Section creation order**: New sections appear at top. The execute script
   creates in reverse order so the final top-to-bottom order matches your YAML.

8. **Dormant channels / "Active only" mode**: Slack hides channels with no
   messages in 30+ days. These channels are NOT in the DOM at all. Both scripts
   switch to "All activity" via the sidebar cog menu before operating:
   `[data-qa="sweeper_button"]` → click "Filter and sort" (`[role="menuitem"]`)
   → click "All activity" (`[role="menuitemcheckbox"]`). Three clicks, menus
   dismiss on selection.

9. **Virtual list coordinate trap**: `page.mouse.click(x, y)` does NOT work
   on the virtualised sidebar — the list uses absolute positioning and
   `transform: translateY()` so viewport coords ≠ element coords. Always use
   `element.click(button="right", force=True)` instead.

10. **force=True is mandatory**: Right-clicks on treeitem elements must use
    `force=True` because the virtualised list may position elements partially
    off-screen or behind overlays.

11. **Submenu triggers open on hover**: Context menu submenus (Move channel,
    Create, Manage) open when you **hover** the `submenu_trigger_wrapper`, not
    when you click it. Clicking may dismiss the parent menu.

12. **Section items appear twice in submenu DOM**: Each section in the Move
    Channel submenu has both a wrapper (`data-qa="section-X-wrapper"`) and
    a clickable item (`data-qa="section-X"`). Filter with
    `:not([data-qa$="-wrapper"])`.

## Don't

- Don't use heredocs (`<< 'EOF'`) in terminal — broken in VS Code terminals.
  Write temp files to `/tmp/` instead.
- Don't run Playwright headless for login — SSO requires a visible browser.
- Don't skip the dry-run step before real execution.
- Don't run execute-reorg without showing the user the action plan first.
- Don't use `:has-text()` selectors for channel matching — elements contain
  icons, badges, and other text that causes false matches. Use
  `query_selector_all` + exact text comparison instead.
- Don't use `page.mouse.click(x, y)` or `dispatchEvent` for right-clicks —
  neither works with the virtualised sidebar. Use `element.click()` only.
