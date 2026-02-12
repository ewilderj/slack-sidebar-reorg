# slack-sidebar-reorg

Automate Slack sidebar organization using Playwright browser automation. Design
a layout, then execute it — channels get sorted into sections with emoji,
automatically.

Built as a [GitHub Copilot CLI](https://githubnext.com/projects/copilot-cli)
skill, but the scripts work standalone too.

## How it works

1. **Extract** your current sidebar layout (`scripts/extract-sidebar`)
2. **Design** a target layout (YAML config with sections, emoji, and channel assignments)
3. **Diff** current vs. desired to produce an action plan (`scripts/diff-layout`)
4. **Execute** the plan via Playwright (`scripts/execute-reorg`)
5. **Verify** by re-extracting and re-diffing until everything matches

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (scripts are self-contained with inline dependencies)
- Playwright with Chromium (`uv run --script scripts/login` handles setup)

## Quick Start

### 1. Login to Slack

```bash
uv run scripts/login --workspace https://mycompany.slack.com
```

This opens a browser for SSO authentication. Your session is saved to
`~/.slack-reorg/sessions/{workspace}/` for reuse.

### 2. Extract current sidebar

```bash
uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > sidebar.json 2>extract.log
```

### 3. Create a layout config

Create a YAML file describing your desired sidebar sections:

```yaml
workspace: https://mycompany.slack.com
sections:
  - name: "🔥 My Team"
    channels:
      - team-chat
      - team-standup
      - team-random
  - name: "🚀 Projects"
    channels:
      - project-alpha
      - project-beta
  - name: "📦 Low Signal"
    channels:
      - general
      - random
      - announcements

# Sections to leave untouched (e.g., DMs, Apps)
keep_sections:
  - Direct messages
  - Apps
```

### 4. Generate an action plan

```bash
uv run scripts/diff-layout --current sidebar.json --desired layout.yaml --pretty
# Save the plan:
uv run scripts/diff-layout --current sidebar.json --desired layout.yaml > action-plan.json
```

### 5. Execute

```bash
# Dry run first
uv run scripts/execute-reorg --plan action-plan.json --workspace https://mycompany.slack.com --dry-run

# Execute for real
uv run scripts/execute-reorg --plan action-plan.json --workspace https://mycompany.slack.com
```

### 6. Verify and retry

The execute script may not move all channels in a single pass.
Always verify:

```bash
# Re-extract
uv run scripts/extract-sidebar --workspace https://mycompany.slack.com > sidebar-after.json 2>extract.log

# Re-diff
uv run scripts/diff-layout --current sidebar-after.json --desired layout.yaml --pretty

# If moves remain, re-run (skipping delete/create since sections exist):
uv run scripts/execute-reorg --plan action-plan.json --workspace https://mycompany.slack.com --skip-phases delete create
```

Repeat until diff shows zero moves.

## Using as a Copilot CLI Skill

Copy or symlink this repo into your skills directory (e.g.,
`~/.github/skills/slack-reorg/`). The `SKILL.md` file tells the Copilot agent
how to orchestrate the full workflow interactively.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/login` | Authenticate with Slack via browser SSO |
| `scripts/extract-sidebar` | Extract current sidebar layout as JSON |
| `scripts/diff-layout` | Compare current vs. desired layout, output action plan |
| `scripts/execute-reorg` | Execute action plan via Playwright |
| `scripts/session_helper.py` | Shared session/path utilities |

## How the execution works

- **Phase 1 — Delete**: Removes existing custom sections (channels fall to "Channels")
- **Phase 2 — Create**: Creates fresh sections with emoji (in reverse order so top-down matches config)
- **Phase 3 — Move**: Linear scan of the sidebar, moving channels to target sections

The delete-first strategy ensures emoji are always set correctly and avoids
conflicts with existing sections.

## Known limitations

- Slack Connect channels and DMs cannot be moved between sections (automatically skipped)
- Common section names like "Social" trigger Slack's suggestion UI (handled automatically)
- Virtualised sidebar means only ~20 channels are in the DOM at once (scripts scroll to find items)
- ~5 seconds per channel move due to menu interaction timing

## License

MIT — see [LICENSE](LICENSE).
