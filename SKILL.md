---
name: slack-reorg
description: >
  Design and execute Slack sidebar reorganizations. Two phases: (1) Design —
  extract sidebar, propose sections, let user refine. (2) Execute — puppet the
  Slack UI via Playwright to create sections, move channels, and clean up.
  Use when user wants to tidy Slack, reorganize channels, review sidebar layout,
  or bulk-move channels between sections.
---

# Skill: Slack Sidebar Reorganization

Two-phase workflow: **Design** a layout, then **Execute** it. These phases are
independent — the user may design now and execute later, or skip straight to
execution with an existing config.

**IMPORTANT: Before starting, ask the user for their Slack workspace URL**
(e.g., `https://mycompany.slack.com`). All scripts require `--workspace` —
there is no default. Use this URL consistently in every command throughout
the session.

## When to Activate

| User says | Phase | Action |
|-----------|-------|--------|
| "show my Slack sidebar" / "what's in my sidebar" | Design | `scripts/extract-sidebar` |
| "organize my Slack" / "propose a Slack reorg" | Design | Extract → design with user → save config |
| "tidy my Slack" / "reorganize Slack" | Both | Design → confirm → execute |
| "execute the Slack reorg" / "apply the layout" | Execute | `scripts/diff-layout` → `scripts/execute-reorg` |
| "what would change?" / "dry run" | Execute | `scripts/diff-layout` (show plan only) |
| "add channel X to section Y" | Execute | Edit config YAML, then diff + execute |
| "move all tmp- channels to In Flight" | Execute | Edit config YAML, then diff + execute |

---

## First-Time Setup

Before any Design or Execute phase, the user needs a working Playwright session
with Slack SSO. Run the login script — it handles everything:

```bash
uv run scripts/login --workspace https://mycompany.slack.com
```

This will:
1. Check if Playwright is installed; attempt to install it if not
2. Install the Chromium browser if missing (`playwright install chromium`)
3. Open a visible Chromium browser pointed at the Slack workspace
4. Wait for the user to complete SSO login (up to 5 minutes)
5. Persist the session to `~/.slack-reorg/sessions/{workspace-hostname}/`

After login, all other scripts automatically find the session — no need to pass
`--session-dir` unless you want to override the default location.

**Session storage**: `~/.slack-reorg/sessions/{workspace-hostname}/`
(e.g., `~/.slack-reorg/sessions/mycompany.slack.com/`)

If a session expires, just run `scripts/login` again to re-authenticate.

---

## Phase 1: Design

### Step 1 — Extract current sidebar

**IMPORTANT: Always redirect output to a file.** The extraction launches a
browser and takes 30-60 seconds — never run it without saving the output.

```bash
uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > /tmp/sidebar.json 2>/tmp/extract.log
```

Then read `/tmp/sidebar.json` for the structured data and `/tmp/extract.log`
for diagnostics. Do NOT run extraction a second time just to inspect output —
read the saved file instead.

### Step 2 — Design a layout with the user

Read the extracted sidebar JSON and design a layout collaboratively:

1. **Ask the user** about their role, what they check daily, which teams they
   belong to, and what channels are noise
2. **Analyze** channel names for natural groupings (common prefixes, suffixes,
   keywords)
3. **Propose** sections following the principles in
   [references/DESIGN_GUIDE.md](references/DESIGN_GUIDE.md)
4. **Iterate** — refine based on user feedback until they approve
5. **Save** the final config as a YAML file (e.g., `~/.slack-reorg/layout.yaml`)
6. Present the final layout for approval before proceeding to Phase 2

**Design principles** — see [references/DESIGN_GUIDE.md](references/DESIGN_GUIDE.md)

### Config format

The YAML config is consumed by `scripts/diff-layout`. It must follow this
schema exactly — the agent produces this file during the Design phase.

```yaml
# Required: the Slack workspace URL
workspace: https://mycompany.slack.com

# Required: list of sections in desired top-to-bottom order
sections:
  - name: "🔥 Daily Ops"          # Section name (emoji prefix optional)
    channels:                      # List of channel names (without #)
      - incident-command
      - announcements

  - name: "📦 Low Noise"
    channels:
      - how-do-i
      - blogroll

# Optional: sections to leave completely untouched
# Only use for sections you want to keep as-is (e.g., Starred).
# Do NOT put External Connections here — sort those channels into sections.
keep_sections:
  - Starred
```

**Schema rules** (the agent MUST follow these when generating):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `workspace` | string | Yes | Full Slack workspace URL |
| `sections` | list | Yes | Ordered list of section objects |
| `sections[].name` | string | Yes | Section display name, may include leading emoji |
| `sections[].channels` | list of strings | Yes | Channel names without `#`, lowercase |
| `keep_sections` | list of strings | No | Section names to leave untouched |

**Constraints:**
- Each channel must appear in exactly one section (no duplicates)
- Channel names must match what appears in the sidebar (lowercase, hyphens)
- Section names can include emoji (e.g., `"🔥 Daily Ops"`) — the execute script
  handles splitting the emoji and setting it via the picker
- Section order in the YAML = desired sidebar order (top to bottom)
- Sections in the current sidebar that don't appear in the config AND aren't
  in `keep_sections` will be **deleted** (except built-in sections like Starred,
  VIP unreads, External Connections — these are never deleted)
- Channels not assigned to any section are flagged as warnings but left in place
- **External Connections** channels (Slack Connect) are regular channels — assign
  them to sections like any other channel. Don't leave them in `keep_sections`.

---

## Phase 2: Execute

### Step 1 — Generate action plan

```bash
uv run scripts/diff-layout \
  --current /tmp/sidebar.json \
  --desired configs/username.yaml \
  > /tmp/action-plan.json
```

Outputs a JSON action plan:
```json
{
  "create_sections": ["🔥 Daily Ops", "📦 Low Noise"],
  "moves": [
    {"channel": "design-team", "from": "General", "to": "👥 My Team"},
    {"channel": "api-eng", "from": "Engineering", "to": "🔧 Engineering"}
  ],
  "delete_sections": ["Workstreams", "My team"],
  "warnings": ["channel 'unknown-channel' in config but not in sidebar"]
}
```

**Show this plan to the user and get explicit approval before executing.**

### Step 2 — Execute (with approval)

```bash
# Dry run first (always)
uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com --dry-run

# Then execute for real
uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com
```

Override session dir if needed:
```bash
uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com --session-dir /custom/path
```

Resume after a failure (skip delete/create, re-scan moves from scratch):
```bash
uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com --skip-phases delete create
```

The execute script:
- Deletes sections → creates sections → moves channels (3 phases)
- `--skip-phases delete create` skips phases 1 & 2 (scan handles already-sorted channels)
- Exits with code 1 if any operations failed
- Is idempotent — safe to re-run if interrupted

**Timing**: ~5s per channel move.

### Step 3 — Verify and Retry (MANDATORY)

**The execute script's self-reported results are unreliable.** It may report
success while channels remain unsorted. After EVERY execution run:

1. **Re-extract the sidebar** to see actual state:
   ```bash
   uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > /tmp/sidebar-after.json 2>/tmp/extract.log
   ```

2. **Re-run diff-layout** against the same desired config:
   ```bash
   uv run scripts/diff-layout --current /tmp/sidebar-after.json --desired /path/to/layout.yaml --pretty
   ```

3. **If moves remain**, re-run execute-reorg with `--skip-phases delete create`:
   ```bash
   uv run scripts/execute-reorg --plan /tmp/action-plan.json --workspace https://mycompany.slack.com --skip-phases delete create
   ```

4. **Repeat steps 1–3** until diff-layout shows zero moves remaining.

**Do NOT tell the user the reorg is complete until a verification extract
confirms all channels are in their target sections.**

### Error handling

See [references/PUPPET_STRATEGY.md](references/PUPPET_STRATEGY.md) for:
- DOM selectors and gotchas
- Interstitial page handling
- Duplicate `data-qa` disambiguation
- Virtualized sidebar scrolling
- Modal dismissal

---

## File Reference

| File | Purpose |
|------|---------|
| `scripts/login` | First-time setup: install Chromium, SSO login, persist session |
| `scripts/session_helper.py` | Shared session management (paths, Playwright checks) |
| `scripts/extract-sidebar` | Playwright: scroll sidebar, output JSON |
| `scripts/diff-layout` | Pure Python: current JSON vs desired YAML → action plan |
| `scripts/execute-reorg` | Playwright: execute action plan on live Slack |
| `configs/*.yaml` | Per-user layout configs |
| `references/DESIGN_GUIDE.md` | Principles for designing a good reorg |
| `references/PUPPET_STRATEGY.md` | Tested DOM selectors and automation strategy |

## Dependencies

- Python 3.11+
- `uv` (handles all Python dependency management automatically)
- Chromium browser (installed via `uv run -m playwright install chromium`, or
  automatically by `scripts/login`)

Each script declares its own dependencies via PEP 723 inline script metadata.
No venv setup needed — `uv run` handles everything.

## Important Notes

- **First time?** Run `uv run scripts/login` — it handles Playwright setup
  and Slack SSO in one step.
- **Never execute without user approval.** Always show the action plan first.
- **Dormant channels**: Slack's Channels section defaults to "Active only"
  mode, which hides channels with no messages in 30+ days. These hidden
  channels are completely absent from the sidebar DOM. Both `extract-sidebar`
  and `execute-reorg` automatically switch to "All" mode before operating
  and restore "Active only" afterwards. If you see channels missing from
  extraction results, this is likely the cause.
- Session profiles are stored in `~/.slack-reorg/sessions/` — one directory per
  workspace. If a session expires, re-run `scripts/login` to refresh.
- Slack's DOM is subject to change. If selectors break, update
  `references/PUPPET_STRATEGY.md` and the execute script together.
- The sidebar is virtualized — only ~92 items render at once. Scripts handle
  scrolling automatically.
