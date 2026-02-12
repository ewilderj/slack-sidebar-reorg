# Slack Sidebar Puppeting Reference

DOM structure, verified selectors, and gotchas for automating Slack's sidebar
with Playwright. Keep this updated when Slack changes its UI.

Last verified: 2026-02-11

## Prerequisites

- **Playwright persistent context** with a persisted SSO session
- **Chromium launch flag**: `--disable-features=ExternalProtocolDialog` (suppresses "Open in Slack app?" dialog)
- **URL pattern**: Use `/messages/{channel}` (NOT `/archives/` — triggers extra redirects)

## Navigation

Slack shows a "Launch in app" interstitial on every URL open:

1. Navigate to workspace URL + `/messages/general`
2. Check title for "Redirect" / "Launch"; if present, click `a:has-text("browser")`
3. Wait for sidebar: `[role="tree"][data-qa="slack_kit_list"]` (45s timeout is safe)

## Sidebar DOM Structure

| Element | Selector |
|---------|----------|
| Sidebar tree | `[role="tree"][data-qa="slack_kit_list"]` |
| Section header | `[role="treeitem"][aria-expanded]` (level 1) |
| Section heading label | `[data-qa^="channel_sidebar__section_heading_label__"]` |
| Section heading toggle | `[data-qa^="section_heading_toggle_and_label__"]` |
| Section ellipsis (hover) | `[data-qa^="section_heading_button_ellipsis__"]` |
| Channel item | `[data-qa="channel-sidebar-channel"]` inside `[role="treeitem"]` |

- **Virtualized list** — only ~92 items rendered at once; must scroll in 80px steps
- **No drag-and-drop** — all operations via context menus only
- **Built-in sections** (Starred, VIP unreads, External Connections, Channels, Direct messages, Apps) have different context menus — custom sections have "Create" submenu, built-in ones don't

### Dormant Channels ("Active only" mode)

The built-in "Channels" section has a **"Show and sort"** preference that
defaults to **"Active only"**. This hides channels with no messages in 30+ days.
These hidden channels are **not in the sidebar DOM at all** — no amount of
scrolling will find them.

**To reveal dormant channels before extraction or moving:**

Use the sidebar "Manage my sidebar" cog button → "Filter and sort" → "All activity".
This is a workspace-wide setting that shows all channels including dormant ones.

```python
# Step 1: Click the cog button
cog = await page.query_selector('[data-qa="sweeper_button"]')
await cog.click(force=True)
await page.wait_for_timeout(1500)

# Step 2: Click "Filter and sort" menu item
items = await page.query_selector_all('[role="menuitem"]')
for item in items:
    text = (await item.text_content() or "").strip()
    if text.startswith("Filter and sort"):
        await item.click(force=True)
        break
await page.wait_for_timeout(1500)

# Step 3: Click "All activity" in the submenu (role="menuitemcheckbox")
submenu_items = await page.query_selector_all(
    '[role="menuitemradio"], [role="menuitemcheckbox"]')
for item in submenu_items:
    text = " ".join((await item.text_content() or "").split())
    if "All activity" in text:
        await item.click()
        break
await page.wait_for_timeout(2000)
```

| Element | Selector |
|---------|----------|
| Cog button | `[data-qa="sweeper_button"]` (aria-label="Manage my sidebar") |
| Filter and sort | `[role="menuitem"]` matching text starting with "Filter and sort" |
| All activity | `[role="menuitemcheckbox"]` matching text "All activity" |

## Right-Clicking Channels (Virtualized List)

The virtualized list complicates right-clicking channels. Only one approach
works reliably:

### ✅ Working approach: `treeitem.click(button="right", force=True)`

```python
treeitems = await page.query_selector_all('[role="treeitem"]')
for ti in treeitems:
    ch = await ti.query_selector('[data-qa="channel-sidebar-channel"]')
    if ch:
        text = await ch.text_content()
        if text and text.strip() == channel_name:
            await ti.click(button="right", force=True)
            break
```

### ❌ `page.mouse.click(x, y)` — DOES NOT WORK

`getBoundingClientRect()` returns coordinates relative to the scroll container,
not the viewport. A channel at scroll position 2357px returns `y=2357` even
though the viewport is only 900px tall. The click lands on the wrong element
or off-screen entirely.

### ❌ `dispatchEvent(new MouseEvent("contextmenu"))` — DOES NOT WORK

Slack uses React's synthetic event system. Native DOM events dispatched via
`dispatchEvent` are not picked up by React event handlers, so the context menu
never appears.

### ❌ `page.locator(':text-is("channel-name")')` — DOES NOT WORK

Channel elements contain icons, badges, and whitespace in addition to the
channel name. `:text-is()` requires an exact match on text content, so it
times out.

### Element detachment risk

After scrolling, the virtual list may recycle DOM elements before you can
click them. **Find AND click in the same scroll position** — don't scroll
between finding a channel and right-clicking it.

## Verified Selectors (as of 2026-02-11)

### Section Context Menu (right-click on section treeitem)

Right-click a **custom** section header (not built-in) to get:

| Element | Selector |
|---------|----------|
| Share section | `[data-qa="share_channel_set"]` |
| "Create" submenu trigger | `[data-qa="channel_section_submenu_create"]` |
| "Manage" submenu trigger | `[data-qa="channel_section_submenu_manage"]` |
| Show and sort | `[data-qa="channel_section_menu_show_sort_pref"]` |

**Important:** These are submenu triggers, not direct items. You must **hover
the `[data-qa="submenu_trigger_wrapper"]`** parent to open the submenu, then
click the actual item inside.

### Create Section Dialog

To open: right-click custom section → hover "Create" wrapper → click "Create section"

| Element | Selector |
|---------|----------|
| Submenu trigger wrapper | `[data-qa="submenu_trigger_wrapper"]` (filter by text "Create") |
| "Create section" menu item | `[data-qa="channel_section_menu_create_new_section"]` |
| Section name input | `[data-qa="channel-section-search-select-input"]` (role=combobox) |
| Emoji picker button | `[data-qa="channel_selection_modal_input_emoji_picker"]` |
| Create button | `[data-qa="channel_selection_modal_input_go"]` or `button:has-text("Create")` |
| Cancel button | `[data-qa="channel_selection_modal_input_cancel"]` |
| Close button | `[data-qa="channel_selection_modal_input_close"]` |

### Emoji Picker (inside create-section dialog)

| Element | Selector |
|---------|----------|
| Picker container | `[data-qa="emoji-picker"]` |
| Search input | `[data-qa="emoji_picker_input"]` (placeholder "Search all emoji") |
| Emoji result item | `button[data-qa="emoji_list_item"]` (role=gridcell) |
| Category tabs | `[data-qa="emoji_group_tab_*"]` (e.g. `emoji_group_tab_search`) |

### Channel Context Menu (right-click on channel treeitem)

| Element | Selector |
|---------|----------|
| Move channel | `[data-qa="channel_ctx_menu_move"]` (**shared** — see gotcha #1) |
| Move submenu wrapper | `[data-qa="submenu_trigger_wrapper"]` (filter text "Move channel") |
| Section list in move submenu | `[data-qa^="section-"]:not([data-qa$="-wrapper"])` |

**Moving a channel — full sequence:**

1. Right-click channel treeitem with `force=True`
2. Find `[data-qa="channel_ctx_menu_move"]` items, filter for text starting with "Move channel" (not "Edit notifications")
3. Find `[data-qa="submenu_trigger_wrapper"]` containing "Move channel" text → **hover** it
4. Wait 1s for submenu to appear
5. Find `[data-qa^="section-"]:not([data-qa$="-wrapper"])` items
6. Match by text content (section names are plain text, no emoji)
7. Click the matched section item

### Section Manage Submenu

| Element | Selector |
|---------|----------|
| "Manage" submenu trigger | `[data-qa="channel_section_submenu_manage"]` |
| Mute all | `[data-qa="channel_section_menu_mute"]` |
| Delete section | `[data-qa="channel_section_menu_remove_channel_section"]` |
| Rename section | `[data-qa="channel_section_menu_rename_channel_section"]` |

## Scroll Container

The scroll container wrapping the sidebar tree is found by walking up from the
tree element looking for `overflow-y: auto|scroll`:

```python
async def scroll_to(page, position):
    await page.evaluate('''(pos) => {
        const tree = document.querySelector('[role="tree"][data-qa="slack_kit_list"]');
        let el = tree;
        while (el) {
            const s = window.getComputedStyle(el);
            if (s.overflowY === 'auto' || s.overflowY === 'scroll') {
                el.scrollTop = pos;
                return;
            }
            el = el.parentElement;
        }
    }''', position)
```

Use 80px scroll steps. Items are ~28-36px tall, so 80px ensures overlap.

## Modal / Menu Dismissal

**Critical pattern:** Always dismiss lingering overlays between operations.
ReactModal overlays (`<div class="ReactModal__Overlay">`) block pointer events
on elements underneath.

```python
async def dismiss_all(page):
    for _ in range(5):
        has = await page.evaluate('''() =>
            !!document.querySelector('.ReactModal__Overlay') ||
            !!document.querySelector('[role="menu"]')
        ''')
        if has:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        else:
            break
```

Call this before any operation that requires clicking sidebar elements.

## Gotchas

1. **`channel_ctx_menu_move` is ambiguous** — both "Edit notifications" and "Move channel" share this `data-qa` value. Always filter by text content: `text.startswith("Move channel")`.

2. **Section name input is `role="combobox"`** — use `.fill()` not `.type()`. It has autocomplete behavior.

3. **Create button uses `aria-disabled`** — Slack sets `aria-disabled="true"` instead of the HTML `disabled` attribute. Check `aria-disabled` before clicking.

4. **ReactModal overlays persist after section creation** — always dismiss with multiple Escape presses after creating a section, or the overlay blocks all subsequent actions. Check for `.ReactModal__Overlay` in DOM.

5. **New sections appear at the top** — create in reverse order so the final ordering matches your desired layout.

6. **Built-in sections have different menus** — right-clicking "Starred", "VIP unreads", or "Channels" shows a different context menu than custom sections. Use custom sections as right-click targets for "Create section".

7. **Emoji picker button can match reactions** — the old `button[aria-label*="emoji"]` selector hits message reaction buttons too. Always use the specific `data-qa` selector.

8. **Dormant channels are invisible** — the "Channels" section defaults to "Active only" which hides channels with no messages in 30+ days. These are NOT in the DOM. Must switch to "All" mode before extraction or moving, then switch back after.

9. **Section ellipsis buttons are hidden until hover** — the `section_heading_button_ellipsis__*` buttons only appear when hovering the section heading. Use `force=True` if clicking them directly, or hover the heading first.

10. **Move submenu requires hovering, not clicking** — the "Move channel" context menu item has a submenu. You must **hover** the `submenu_trigger_wrapper` parent to open the submenu. Clicking the menu item itself does nothing useful.

11. **Section items in move submenu appear twice** — each section appears as both a `section-{id}-wrapper` and `section-{id}`. Use `:not([data-qa$="-wrapper"])` to get only the clickable item.

12. **Virtual list coordinates are misleading** — `getBoundingClientRect()` returns positions relative to the scroll container, not the viewport. Use Playwright element handles (`.click()`) instead of `page.mouse.click(x, y)`.

13. **Items may use different CSS positioning** — some sidebar items use `top: Xpx`, others use `transform: translateY(Xpx)`, and some have neither. Extraction must check both styles and fall back to `offsetTop`.
