---
name: wp-cli
description: WordPress management via REST API — posts, pages, media, taxonomy, ACF fields, schema, guarded publishing (slug-guard, markdown-leak, em-dash, drift), SEO meta (RankMath/Yoast/generic with focus-keyword merge), comments, plugins, users, search, menus, widgets, and settings. Use when the user wants to create, update, list, delete, schedule, or safely publish WordPress content, upload/optimize images, manage taxonomy/custom fields/structured data, moderate comments, manage plugins/users/menus/widgets, search content, or read/update site settings.
---

# WordPress CLI

Manage WordPress sites via the REST API. All commands require `--site <site_id>` and must be run from the skill directory.

**Run commands with:** `export CLAUDE_SKILL_CALLER_CWD="$(pwd)" && cd "${CLAUDE_SKILL_DIR}" && python -m cli.main --site <id> <resource> <action> [options]`

## Available Operations

### Posts
- `posts list [--status draft|publish|any] [--per-page 10] [--page 1]`
- `posts get --id <post_id>`
- `posts create --title "..." [--content-file draft.md] [--status draft] [--date 2026-03-20T09:00:00] [--category-ids 1,2] [--tag-ids 3,4] [--featured-media 456]`
- `posts update --id <post_id> [--title "..."] [--content-file updated.md] [--status publish] [--date 2026-03-20T09:00:00] [--featured-media 456]`
- `posts delete --id <post_id> [--force]`
- `posts revisions --id <post_id>`

### Pages
- `pages list [--status draft|publish|any]`
- `pages get --id <page_id>`
- `pages create --title "..." [--content-file page.md] [--parent-id 10] [--template full-width]`
- `pages update --id <page_id> [--title "..."] [--status publish]`
- `pages delete --id <page_id> [--force]`

### Media
- `media list [--media-type image|video] [--per-page 10]`
- `media get --id <media_id>`
- `media upload --file image.png [--alt-text "..."] [--caption "..."] [--title "..."]`
- `media delete --id <media_id> [--force]`

### Taxonomy
- `taxonomy categories list`
- `taxonomy categories create --name "SEO" [--parent-id 5]`
- `taxonomy categories delete --id 8`
- `taxonomy tags list`
- `taxonomy tags create --name "wordpress"`
- `taxonomy tags delete --id 12`

### Fields (ACF)
- `fields get --post-id 123`
- `fields update --post-id 123 --data '{"field": "value"}'`

### Schema
- `schema get --post-id 123`
- `schema push --post-id 123 --schema-file faq.json`
- `schema push --post-id 123 --data '{"@type": "FAQPage", ...}'`

### Publish (guarded — safe body push)
Refuses on slug mismatch, raw-markdown leak, or significant drift; strips em-dashes; strips a leading "Meta description:" artifact.
- `publish fetch --id 123 [--type post|page]` — fetch live raw content before editing
- `publish push --id 123 --content-file body.html [--slug expected-slug] [--status draft|publish|future|pending|private] [--type post|page] [--force] [--no-emdash-strip] [--allow-drift] [--no-drift-check]`

### SEO Meta (RankMath / Yoast / generic; plugin auto-detected)
Focus keywords MERGE with `--focus-add` (skipped with a warning if the site's existing keywords are unreadable, e.g. RankMath without a getMeta route); `--focus-set` replaces. Unset title/description are never clobbered.
- `meta get --id 123 [--plugin auto|rankmath|yoast|generic] [--type post|page]`
- `meta set --id 123 [--title "..."] [--desc "..."] [--focus-add "kw1,kw2"] [--focus-set "kw1,kw2"] [--plugin auto] [--type post|page]`

### Comments
- `comments list [--status approve|hold|spam|trash] [--post 123] [--per-page 20]`
- `comments get --id 45`
- `comments approve|hold|spam --id 45`
- `comments reply --post 123 --parent 45 --content "..."`
- `comments create --post 123 --content "..." [--parent 45]` (post must be published — WP forbids comments on drafts)
- `comments delete --id 45 [--force]`

### Plugins
- `plugins list [--status active|inactive]`
- `plugins get --plugin "akismet/akismet"`
- `plugins activate|deactivate --plugin "akismet/akismet"`
- `plugins install --slug classic-editor [--activate]`
- `plugins delete --plugin "akismet/akismet"`

### Users
- `users list [--per-page 20]`
- `users get --id 5`
- `users create --username u --email e@x.com --password "..." [--role author]`
- `users update --id 5 [--email ...] [--role editor] [--name "..."]`
- `users delete --id 5 [--reassign 1]`

### Search
- `search --term "claude" [--type post|term|post-format] [--subtype post] [--per-page 10]`

### Menus
- `menus list`
- `menus get --id 16`
- `menus create --name "Main" [--locations primary,footer]`
- `menus delete --id 16`
- `menus items --menu-id 16`
- `menus add-item --menu-id 16 --title "Home" [--url ...] [--object-id 12 --object page --type post_type] [--parent 0]`
- `menus delete-item --id 99`
- `menus assign-location --id 16 --locations primary`

### Widgets
- `widgets sidebars`
- `widgets sidebar --id sidebar-1`
- `widgets list`
- `widgets types`

### Settings
- `settings get [--key title]`
- `settings set --key title --value "My Site"` (value parsed as JSON when possible, else string)

## Scheduling Posts

To schedule a post for future publication, set both status and date:
```
posts update --id 123 --status future --date 2026-03-25T09:00:00
```

## Setting Featured Images

Upload an image first, then assign it:
```
media upload --file hero.webp --alt-text "Description" --title "Hero Image"
posts update --id 123 --featured-media <media_id>
```

## Image Optimization Workflow

1. Download the image from WordPress
2. Read the image with Claude Code's vision to generate alt text
3. Convert to WebP with Pillow: `img.save('out.webp', 'WEBP', quality=80)`
4. Upload the optimized WebP with the generated alt text
5. Update the post's featured image to the new media ID

## Output

All output is JSON. Check `status` field:
- `"success"` → read `data`
- `"error"` → read `code`, `message`, `http_status`

## Site Configuration

The skill looks for a `sites/` folder in your working directory first, then falls back to `~/.marvomatic/sites/`. Each site is a subfolder with:
- `config.yaml` — WordPress settings (URL, editor type, SEO plugin, etc.)
- `.env.site` — Credentials (username + app password)

So if you run Claude Code from `/my-project/`, your sites live at `/my-project/sites/<site-id>/`.

Resolution order:
1. `MARVOMATIC_SITES_DIR` environment variable (if set)
2. `./sites/` in your current working directory
3. `~/.marvomatic/sites/` (global fallback)

Run `/core:setup` for first-time site configuration.
