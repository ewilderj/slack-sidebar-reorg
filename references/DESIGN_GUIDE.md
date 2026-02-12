# Design Guide: Slack Sidebar Reorganization

Principles and heuristics for designing a good Slack sidebar layout.

## Goals

1. **Find things fast** — channels you need daily are at the top, in small sections
2. **Reduce noise** — channels you rarely check are muted, collapsed, at the bottom
3. **Group by function** — channels in a section share a purpose, not just a prefix
4. **Keep it maintainable** — sections should be stable; channels come and go

## Section Design Principles

### Size targets

| Section type | Target size | Example |
|-------------|-------------|---------|
| Daily ops / hot | 5-10 channels | Things you check every morning |
| Functional group | 15-25 channels | Your team, a product area |
| Large technical bucket | 30-70 channels | All engineering channels for one product |
| Low noise / archive | Any | Muted, collapsed, reviewed quarterly |

### Avoid these patterns

- **One huge bucket** (50+ unsorted channels) — defeats the purpose
- **Too many tiny sections** (2-3 channels each) — scroll noise, no grouping benefit
- **Organizing by Slack's default names** — "Channels" is not a category
- **Mixing daily-check and rarely-check** in the same section
- **Duplicating channels** across sections — each channel belongs to exactly one section

### Section ordering (top to bottom)

1. **Hot / daily** — what you check first thing
2. **Your team** — your org, direct reports, management function
3. **Strategic** — leadership, decision-making, strategy channels
4. **Active work** — launches, projects, time-bounded initiatives
5. **Domain groups** — infrastructure, security, product areas
6. **Broad org** — company-wide, governance, community
7. **Social** — fun, watercooler, interest groups
8. **Low noise** — muted, rarely checked, reference channels
9. **Temporary** — tmp- channels, time-boxed initiatives

## Heuristic Groupings

When proposing sections from raw sidebar data, use these channel name patterns:

| Pattern | Likely section |
|---------|---------------|
| `tmp-*` | Temporary / In Flight |
| `*-launch` | Active Launches |
| `security-*` | Security & Compliance |
| `infra-*`, `platform-*` | Infrastructure |
| `eng-*` | Engineering |
| `program-*`, `project-*` | Program Management |
| `*-lt`, `*-slt` | Leadership channels |
| `*-ops` | Operations |

Strategy keywords (for splitting leadership from engineering):
- Strategy: `leads`, `slt`, `lt`, `directors`, `billing`, `capacity`
- Engineering: `eng`, `api`, `sdk`, `cli`, `infra`, `support`

## User Interview Questions

When designing for someone, ask:

1. **What's your role?** (determines which channels are "daily ops")
2. **What do you check first every morning?** (→ Daily Ops section)
3. **What teams/orgs do you lead or belong to?** (→ "My Team" section)
4. **Are there channels you're in but never read?** (→ Low Noise or leave)
5. **Do you have tmp- channels for active initiatives?** (→ In Flight)
6. **Any channels that are purely social/fun?** (→ Social section)
7. **Preferred section count?** (most people do well with 8-15 sections)

## Iterating on the Layout

The config YAML is the source of truth. To iterate:

1. Edit the YAML (move channels between sections, rename sections)
2. Re-run `diff-layout` to see what changes
3. If the user wants a completely fresh start, re-run `propose-layout`

The agent should present changes as a readable summary, not raw YAML, e.g.:

> **Proposed changes:**
> - Create "🔥 Daily Ops" with 7 channels (incident-command, announcements, ...)
> - Move 25 channels from "Product" to "Product Engineering"
> - Move 14 channels from "Product" to "Product Strategy"
> - Mute all 21 channels in "Low Noise"
> - Delete empty sections: Workstreams, My team

## Maintenance

After initial reorganization:
- **New channels**: Add to the appropriate section in the YAML, re-run
- **Leave a channel**: Remove from the YAML (it becomes "unassigned" — warning on next diff)
- **Seasonal cleanup**: Re-run extract → diff to see drift from desired layout
- **Share with colleagues**: They copy the YAML structure and adjust channel lists for their own sidebar
